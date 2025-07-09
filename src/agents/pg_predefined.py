from typing import Annotated

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from agents.models import models
from agents.prompts import (
    PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_HUMAN,
    PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_SYS,
    PROMPT_GENERATE_RESPONSE_FROM_SQL,
    PROMPT_GET_REQUIRED_TABLES,
    PROMPT_GET_THE_CORE_SUBJECT,
    sql_queries_output_parser,
    table_names_output_parser,
)
from agents.utils import CustomData, convert_rows_to_markdown
from config import settings
from database.connection import PGConnection
from database.utils import get_sample
from retriever.retriever import PGRetriever

load_dotenv()


# Sends a custom event to the server
async def emit_custom_event(type: str, data: dict, config: RunnableConfig):
    task_custom_data = CustomData(type=type, data=data)
    await task_custom_data.adispatch(config)


class State(TypedDict):
    messages: Annotated[list, add_messages]

    user_query: str
    all_tables: list[str]
    sql_statements: list[str]
    result_langchain_docs: list[dict]
    query_error: str
    core_subject: str


# Gets the table(s) information from the description_table
# So, the LLM can decide which table(s) to query
async def get_tables(state: State, config: RunnableConfig = None):
    user_query: str = state["messages"][-1].content.strip()

    await emit_custom_event(
        type="on_get_tables_start",
        data={
            "query": user_query,
            "tool_call_id": "GetRequiredTables",
        },
        config=config,
    )

    c = PGConnection(settings.POSTGRES_DSN.unicode_string())
    conn = c.get_conn()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM description_table;")
        colnames = [desc[0] for desc in cur.description]
        raw_rows = cur.fetchall()
        rows = [dict(zip(colnames, row)) for row in raw_rows]
    conn.close()

    markdown_table = convert_rows_to_markdown(rows)

    prompt = PROMPT_GET_REQUIRED_TABLES.format(
        user_query=user_query, table_descriptions=markdown_table
    )

    # with open("./test/run/get_tables_prompt.md", "w") as f:
    #     f.write(prompt)

    messages = [HumanMessage(content=prompt)]

    model_name = config["configurable"].get("model", "gemini-2.0")

    m: BaseChatModel = models[model_name] | table_names_output_parser

    response = m.invoke(messages, config)

    await emit_custom_event(
        type="on_get_tables_end",
        data={
            "result": ", ".join(response["table_names"]),
            "tool_call_id": "GetRequiredTables",
        },
        config=config,
    )

    return {"all_tables": response["table_names"]}


# Given the user query and relevant tables to use, this generates the SQL queries
# to be executed or correct the previously generated queries if there is an error
async def generate_table_query(state: State, config: RunnableConfig = None):
    c = PGConnection(settings.POSTGRES_DSN.unicode_string())
    conn = c.get_conn()
    user_query: str = state["messages"][-1].content.strip()

    system_msg = PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_SYS.format()

    all_tables = state["all_tables"]
    all_tables_samples = "\n\n".join(
        [
            get_sample(cursor=conn.cursor(), table_name=table_name)
            for table_name in all_tables
        ]
    )
    human_msg = PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_HUMAN.format(
        user_query=user_query,
        all_tables=all_tables_samples,
        generated_query="\n".join(state.get("sql_statements", [])),
        query_error=state.get("query_error", ""),
    )

    conn.close()

    # with open("./test/run/generate_query_human_msg.md", "w") as f:
    #     f.write(human_msg)

    # with open("./test/run/generate_query_system_msg.md", "w") as f:
    #     f.write(system_msg)

    messages = [SystemMessage(content=system_msg), HumanMessage(content=human_msg)]

    model_name = config["configurable"].get("model", "gemini-2.0")

    m: BaseChatModel = models[model_name] | sql_queries_output_parser

    response = await m.ainvoke(messages, config)

    # with open("./test/run/sql_statements.md", "w") as f:
    #     for query in response["queries"]:
    #         f.write(query + "\n\n")

    return {"sql_statements": response["queries"]}


# This function decides whether to invoke the get_core_subject function
# get_core_subject returns the core subject of the query will be useful for semantic logic
def should_invoke_get_core_subject(state: State, config: RunnableConfig = None):
    if state.get("core_subject", None):
        return "execute_query"

    for sql_statement in state["sql_statements"]:
        if "embedding" in sql_statement:
            return "get_core_subject"

    return "execute_query"


# Gets the core subject from the user query
# The core subject will be useful for semantic logic
# For example, if the user query is "what are the diary products"
# the core subject will be "diary products" which improves the retrieval
async def get_core_subject(state: State, config: RunnableConfig = None):
    user_query: str = state["messages"][-1].content.strip()

    await emit_custom_event(
        type="on_get_core_subject_start",
        data={
            "input": user_query,
            "tool_call_id": "GetCoreSubject",
        },
        config=config,
    )

    m: BaseChatModel = models[config["configurable"].get("model", "gemini-2.0")]
    messages = [
        HumanMessage(content=PROMPT_GET_THE_CORE_SUBJECT.format(user_query=user_query))
    ]
    response = await m.ainvoke(messages, config)

    await emit_custom_event(
        type="on_get_core_subject_end",
        data={
            "result": response.content,
            "tool_call_id": "GetCoreSubject",
        },
        config=config,
    )

    return {"core_subject": response.content}


# Executes the SQL queries and returns the results
# If there is an error, it invokes the generate table query again with the error
async def execute_query(state: State, config: RunnableConfig = None):
    retriever = PGRetriever()
    user_query: str = state["messages"][-1].content.strip()

    user_query = state.get("core_subject", user_query)
    results = {
        "result_langchain_docs": [],
        "query_error": "",
    }

    try:
        for statement in state["sql_statements"]:
            await emit_custom_event(
                type="on_retriever_start",
                data={
                    "sql_query": statement,
                    "user_query": user_query if "embedding" in statement else None,
                    "tool_call_id": "PGRetriever",
                },
                config=config,
            )

            docs = retriever.get_relevant_documents(statement, user_query=user_query)
            results["result_langchain_docs"].append(docs)

            await emit_custom_event(
                type="on_retriever_end",
                data={
                    "result": docs,
                    "tool_call_id": "PGRetriever",
                },
                config=config,
            )
    except Exception as e:
        await emit_custom_event(
            type="on_retriever_error",
            data={
                "error": str(e),
                "tool_call_id": "PGRetriever",
            },
            config=config,
        )

        results = {"result_langchain_docs": "", "query_error": f"Error: {e}"}
        return results

    return results


def should_fix_query(state: State, config: RunnableConfig = None):
    if not state["query_error"]:
        return "generate_response"
    else:
        return "generate_table_query"


# Given the user query and results of the SQL queries, this generates the natural language response
async def generate_response(state: State, config: RunnableConfig = None):
    user_query = state["messages"][-1].content
    result_langchain_docs = state["result_langchain_docs"]

    markdown_table = ""

    for docs in result_langchain_docs:
        if markdown_table:
            markdown_table += "\n\n"
        markdown_table += convert_rows_to_markdown(docs)

    response_generation_prompt = PROMPT_GENERATE_RESPONSE_FROM_SQL.format(
        user_query=user_query,
        query_results=markdown_table,
    )

    # with open("./test/run/response_generation_prompt.md", "w") as f:
    #     f.write(response_generation_prompt)

    messages = [HumanMessage(response_generation_prompt)]

    model_name = config["configurable"].get("model", "gemini-2.0")

    m: BaseChatModel = models[model_name]
    response = await m.ainvoke(messages, config)

    return {"messages": [response]}


graph_builder = StateGraph(State)

graph_builder.add_node("get_tables", get_tables)
graph_builder.add_node("generate_table_query", generate_table_query)
graph_builder.add_node("execute_query", execute_query)
graph_builder.add_node("generate_response", generate_response)
graph_builder.add_node("get_core_subject", get_core_subject)

graph_builder.add_edge(START, "get_tables")
graph_builder.add_edge("get_tables", "generate_table_query")
graph_builder.add_conditional_edges(
    "generate_table_query",
    should_invoke_get_core_subject,
    {"get_core_subject": "get_core_subject", "execute_query": "execute_query"},
)
graph_builder.add_edge("get_core_subject", "execute_query")
graph_builder.add_conditional_edges(
    "execute_query",
    should_fix_query,
    {
        "generate_response": "generate_response",
        "generate_table_query": "generate_table_query",
    },
)
graph_builder.add_edge("generate_response", END)

pg_rag: CompiledStateGraph = graph_builder.compile(
    checkpointer=None,
)

# g = pg_rag.get_graph().draw_mermaid_png()
# with open("./src/agents/pg_agent.png", "wb") as f:
#     f.write(g)
