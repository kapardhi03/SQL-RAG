import json
from typing import Any, AsyncGenerator
from uuid import uuid4

from fastapi import APIRouter, FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolCall, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from agents.pg_agent import pg_rag

# from agents.pg_predefined import pg_rag
from agents.utils import convert_rows_to_markdown
from models.schemas import StreamInput, UserInput
from server.utils import langchain_to_chat_message

router = APIRouter()

# In-memory message store (thread_id -> List[BaseMessage])
thread_messages: dict[str, list] = {}


def parse_input(user_input: UserInput) -> tuple[dict[str, Any], str]:
    run_id = str(uuid4())
    thread_id = user_input.thread_id or run_id

    if thread_id not in thread_messages:
        thread_messages[thread_id] = []

    human_msg = HumanMessage(content=user_input.message)
    thread_messages[thread_id].append(human_msg)

    kwargs = {
        "input": {"messages": thread_messages[thread_id]},
        "config": RunnableConfig(
            configurable={"thread_id": thread_id, "model": user_input.model},
            run_id=run_id,
        ),
    }
    return kwargs, run_id, thread_id


@router.get("/")
async def root():
    return {"message": "Hello World"}


# Endpoint streams a response to the client
@router.post("/stream")
async def agent_stream(user_input: StreamInput) -> StreamingResponse:
    return StreamingResponse(
        message_generator(user_input), media_type="text/event-stream"
    )


async def message_generator(
    user_input: StreamInput,
) -> AsyncGenerator[str, None]:
    agent: CompiledStateGraph = pg_rag
    # The config that will help keep track of the agents phases and events through the graph
    kwargs, run_id, thread_id = parse_input(user_input)

    async for event in agent.astream_events(**kwargs, version="v2"):
        if not event:
            continue

        # Every tool event has a start and ending, the start of the event will be a AIMessage
        # with toolcalls and the end of the event will be a tool message
        new_messages = []
        if (
            event["event"] == "on_chain_end"
            and any(t.startswith("graph:step:") for t in event.get("tags", []))
            and "messages" in event["data"]["output"]
        ):
            msgs = event["data"]["output"]["messages"]
            for msg in msgs:
                if msg.content:
                    new_messages.append(msg)
                    thread_messages[thread_id].append(AIMessage(content=msg.content))

        # Custom events like on_get_core_subject_start, on_get_tables_start used in langgraph
        if event["event"] == "on_custom_event" and "custom_data_dispatch" in event.get(
            "tags", []
        ):
            if event["name"] == "on_get_core_subject_start":
                msg = AIMessage(
                    content="",
                    tool_calls=[
                        ToolCall(
                            name="Get core subject",
                            args={"input": event["data"]["input"]},
                            id=event["data"]["tool_call_id"],
                        )
                    ],
                )
                new_messages = [msg]

            if event["name"] == "on_get_core_subject_end":
                msg = ToolMessage(
                    content=event["data"]["result"],
                    tool_call_id=event["data"]["tool_call_id"],
                )
                new_messages = [msg]

            if event["name"] == "on_retriever_error":
                msg = ToolMessage(
                    content=event["data"]["error"],
                    tool_call_id=event["data"]["tool_call_id"],
                )
                new_messages = [msg]

            if event["name"] == "on_get_tables_start":
                args = {}
                for k, v in event["data"].items():
                    args[k] = v

                msg = AIMessage(
                    content="",
                    tool_calls=[
                        ToolCall(
                            name="identify tables",
                            args={"user_query": args["query"]},
                            id=args["tool_call_id"],
                        )
                    ],
                )
                new_messages = [msg]

            if event["name"] == "on_get_tables_end":
                msg = ToolMessage(
                    content=event["data"]["result"],
                    tool_call_id=event["data"]["tool_call_id"],
                )
                new_messages = [msg]

            if event["name"] == "on_retriever_start":
                args = {}
                for k, v in event["data"].items():
                    args[k] = v

                msg = AIMessage(
                    content="",
                    tool_calls=[
                        ToolCall(
                            name="Postgres Retriever",
                            args={
                                "sql_query": args["sql_query"],
                                "user_query": args["user_query"],
                            },
                            id=args["tool_call_id"],
                        )
                    ],
                )

                new_messages = [msg]

            if event["name"] == "on_retriever_end":
                retrived_docs = event["data"]["result"]
                if len(retrived_docs) == 0:
                    context = "N/A"
                else:
                    context = convert_rows_to_markdown(retrived_docs)

                msg = ToolMessage(
                    content=context,
                    tool_call_id=event["data"]["tool_call_id"],
                )
                new_messages = [msg]

        # All the messages will be converted to the Chatmessage with respective roles
        # and be streamed to client as soon as they are generated
        for message in new_messages:
            try:
                chat_message = langchain_to_chat_message(message, run_id)
                yield f"data: {json.dumps({'status': True, 'data': chat_message.model_dump()})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'status': False, 'data': str(e)})}\n\n"
                continue

    yield "data: DONE!\n\n"


app = FastAPI()
app.include_router(router)
