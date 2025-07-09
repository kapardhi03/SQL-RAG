import uuid
from typing import Annotated, Any, List

# ignore all warnings
from warnings import filterwarnings

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from agents.models import models as union_models
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

filterwarnings("ignore", category=UserWarning)

load_dotenv()
chat_models = union_models.copy()


class State(TypedDict):
    messages: Annotated[list, add_messages]

    user_query: str
    all_tables: list[str]
    sql_statements: list[str]
    result_langchain_docs: Any | list[Any]
    query_error: str
    core_subject: str


class ToolSchema(BaseModel):
    state: State = Field("A State object or dict, following the State schema.")
    config: RunnableConfig = Field(
        "A RunnableConfig object, containing the configuration for the tool."
    )


async def emit_custom_event(type: str, data: dict, config: RunnableConfig):
    task_custom_data = CustomData(type=type, data=data)
    await task_custom_data.adispatch(config)


@tool("GetRequiredTables", args_schema=ToolSchema)
async def get_tables(state: State, config: RunnableConfig):
    """
    Initializes the text-to-SQL pipeline by retrieving metadata from the `description_table`.

    This metadata includes table names and their corresponding descriptions, which are used to help
    the language model identify the most relevant table(s) based on the user's natural language query.
    """
    user_query: str = state["user_query"]

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

    messages = [HumanMessage(content=prompt)]

    model_name = config["configurable"].get("model")

    # with open("test/run/get_tables_prompt.md", "w") as f:
    #     f.write(prompt)

    m: BaseChatModel = chat_models[model_name] | table_names_output_parser

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


@tool("GenerateTableQuery", args_schema=ToolSchema)
async def generate_table_query(state: State, config: RunnableConfig):
    """
    Second step of the text-to-SQL pipeline.

    Generates executable SQL queries using the user's natural language query and a list of selected table names.
    This function must be called with **all table names at once**, not individually per table.

    If a previously generated query fails during execution, this function should be **repeatedly invoked**
    with the original user query and the updated error context (`query_error`)—**no matter how many times an error occurs**.
    Each new error should be passed back into this function to help the LLM iteratively refine the SQL.

    ⚠️ Always include error context when re-calling due to an execution failure.
    """
    c = PGConnection(settings.POSTGRES_DSN.unicode_string())
    conn = c.get_conn()
    user_query: str = state["user_query"]

    system_msg = PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_SYS.format()

    all_tables = state.get("all_tables", [])

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

    messages = [SystemMessage(content=system_msg), HumanMessage(content=human_msg)]

    model_name = config["configurable"].get("model")

    m: BaseChatModel = chat_models[model_name] | sql_queries_output_parser

    # with open("test/run/generate_query.md", "w") as f:
    #     f.write(system_msg)
    #     f.write("\n\n" + human_msg)

    response = await m.ainvoke(messages, config)

    state["query_error"] = ""

    return {"sql_statements": response["queries"]}


@tool("GetCoreSubject", args_schema=ToolSchema)
async def get_core_subject(state: State, config: RunnableConfig):
    """
    Step 2.5 of the text-to-SQL pipeline (Optional).

    Used only for queries that benefit from semantic reasoning to extract the *core subject* of the user's intent.
    Not all queries require this step, but it is helpful for cases where deeper understanding improves retrieval quality.

    This function extracts the main concept or focus from the user query to support the LLM in generating more accurate results.

    Examples:
    1. Query: "What are the dairy products?" → Core subject: "dairy products"
    2. Query: "What are the average taxes for goods and services?" → No clear core subject required because the query is generic / Standard SQL → This step can be skipped

    🔁 Invoke this function **after** `generate_table_query` and **before** `execute_query`, only when semantic refinement is needed.
    """
    user_query: str = state["user_query"]

    await emit_custom_event(
        type="on_get_core_subject_start",
        data={
            "input": user_query,
            "tool_call_id": "GetCoreSubject",
        },
        config=config,
    )

    prompt = PROMPT_GET_THE_CORE_SUBJECT.format(user_query=user_query)

    # with open("test/run/get_core_subject_prompt.md", "w") as f:
    #     f.write(prompt)

    messages = [HumanMessage(content=prompt)]

    model_name = config["configurable"].get("model")

    m: BaseChatModel = chat_models[model_name]

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


@tool("ExecuteQuery", args_schema=ToolSchema)
async def execute_query(state: State, config: RunnableConfig):
    """
    Step 3 of the text-to-SQL pipeline.

    Executes the generated SQL statements and returns the query results.
    This function must be called with **all SQL statements at once**—**do not call it individually for each statement**.

    If any statement fails during execution, the pipeline should **re-invoke the `generate_table_query` step**
    with the corresponding error context (`query_error`). This allows the LLM to analyze the error and regenerate
    a corrected SQL statement.

    🔁 This process should repeat for every failure—if `query_error` is not empty, the pipeline must loop back to `generate_table_query`.
    """
    retriever = PGRetriever()
    user_query: str = state["user_query"].strip()
    core_subject: str = state["core_subject"].strip()

    user_query = core_subject if core_subject else user_query

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


@tool("GenerateResponse", args_schema=ToolSchema)
async def generate_response(state: State, config: RunnableConfig):
    """
    Final step of the text-to-SQL pipeline.

    Generates a natural language response using the user's original query and the results returned from the executed SQL statements.
    The LLM combines both inputs to produce a coherent, context-aware, and user-friendly answer.
    """
    user_query = state["user_query"]
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

    # with open("test/run/response_generation_prompt.md", "w") as f:
    #     f.write(response_generation_prompt)

    messages = [HumanMessage(response_generation_prompt)]

    model_name = config["configurable"].get("model")

    m: BaseChatModel = chat_models[model_name]
    response = await m.ainvoke(messages, config)

    return {"messages": [response]}


@tool("Add")
async def add(numbers: List[int | float]) -> int:
    """
    Adds a list of numbers together.
    """
    return sum(numbers)


@tool("Subtract")
async def subtract(a: int | float, b: int | float) -> int:
    """
    Subtracts the second number from the first.
    """
    return a - b


@tool("Multiply")
async def multiply(a: int | float, b: int | float) -> int:
    """
    Multiplies two numbers together.
    """
    return a * b


@tool("Divide")
async def divide(a: int | float, b: int | float) -> float:
    """
    Divides the first number by the second.
    """
    if b == 0:
        raise ValueError("Cannot divide by zero.")
    return a / b


@tool("Average")
async def average(numbers: List[int | float]) -> float:
    """
    Calculates the average of a list of numbers.
    """
    if not numbers:
        raise ValueError("The list is empty.")
    return sum(numbers) / len(numbers)


available_tools = [
    get_tables,
    generate_table_query,
    get_core_subject,
    execute_query,
    generate_response,
    add,
    subtract,
    multiply,
    divide,
    average,
]
llm_with_tools = {k: v.bind_tools(available_tools) for k, v in chat_models.items()}


async def tool_calling_node(state: State, config: RunnableConfig):
    model: BaseChatModel = llm_with_tools[
        config["configurable"].get("model", "azure-gpt-4.1")
    ]
    return {"messages": [model.invoke(state["messages"])]}


graph_builder = StateGraph(State)

graph_builder.add_node("tool_calling_node", tool_calling_node)
graph_builder.add_node("tools", ToolNode(available_tools))

graph_builder.add_edge(START, "tool_calling_node")
graph_builder.add_conditional_edges("tool_calling_node", tools_condition)
graph_builder.add_edge("tools", "tool_calling_node")
graph_builder.add_edge("tool_calling_node", END)

pg_rag: CompiledStateGraph = graph_builder.compile()


async def test_pg_rag():
    initial_state = {
        "messages": [
            HumanMessage(content="What are the average taxes for goods and services")
        ],
        "all_tables": [],
        "sql_statements": [],
        "result_langchain_docs": [],
        "query_error": "",
        "core_subject": "",
    }
    config = RunnableConfig(
        configurable={"thread_id": "mewmew", "model": "azure-gpt-4.1"},
        run_id="mewmew",
    )
    messages = await pg_rag.ainvoke(initial_state, config=config)
    for m in messages["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_pg_rag())
