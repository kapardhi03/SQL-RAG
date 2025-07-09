from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate

sql_queries_response_schemas = [
    ResponseSchema(
        name="queries",
        type="List[string]",
        description="Should be a list of ONLY ONE SQL queries",
    ),
]
sql_queries_output_parser = StructuredOutputParser.from_response_schemas(
    sql_queries_response_schemas
)

table_names_response_schemas = [
    ResponseSchema(
        name="table_names",
        type="List[string]",
        description="Should be a list of table names",
    ),
]
table_names_output_parser = StructuredOutputParser.from_response_schemas(
    table_names_response_schemas
)

SQL_QUERY_FEW_SHOT_EXAMPLES = [
    {
        "table": "CREATE TABLE Places (PlaceID INT PRIMARY KEY, Location DECIMAL(10, 2), usevec_PlaceDescription TEXT, useembed_PlaceDescription VECTOR(1564));",
        "question": "What are the places near the river banks?",
        "sql_query": """
            WITH semantic_search AS (
                SELECT PlaceID, RANK() OVER (ORDER BY useembed_PlaceDescription <=> %(embedding)s) AS rank
                FROM Places
                ORDER BY useembed_PlaceDescription <=> %(embedding)s
                LIMIT %(k)s
            ),
            keyword_search AS (
                SELECT PlaceID, RANK() OVER (ORDER BY ts_rank_cd(to_tsvector('english', usevec_PlaceDescription), plainto_tsquery('english', %(embedding)s)) DESC) AS rank
                FROM Places
                WHERE to_tsvector('english', usevec_PlaceDescription) @@ plainto_tsquery('english', %(embedding)s)
                ORDER BY ts_rank_cd(to_tsvector('english', usevec_PlaceDescription), plainto_tsquery('english', %(embedding)s)) DESC
                LIMIT %(k)s
            ),
            combined AS (
                SELECT
                    COALESCE(semantic_search.PlaceID, keyword_search.PlaceID) AS PlaceID,
                    COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
                    COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
                FROM semantic_search
                FULL OUTER JOIN keyword_search ON semantic_search.PlaceID = keyword_search.PlaceID
            )
            SELECT p.PlaceID, p.Location, p.usevec_PlaceDescription
            FROM combined c
            JOIN Places p ON c.PlaceID = p.PlaceID
            ORDER BY c.score DESC
            LIMIT %(k)s;
        """,
        "reason": "No explicit indicator for places near river banks; semantic + keyword fusion helps improve retrieval.",
    },
    {
        "table": "CREATE TABLE Products (Id INT, ProductName TEXT, Price DECIMAL(10, 2));",
        "question": "Which product has the highest price?",
        "sql_query": "SELECT Id, ProductName, Price FROM Products ORDER BY Price DESC LIMIT 1;",
        "reason": "Straightforward SQL to find highest price, no semantic search needed.",
    },
    {
        "table": "CREATE TABLE Goods (id INT, Name TEXT, Tax DECIMAL(10, 2), usevec_Description TEXT, useembed_Description VECTOR(1564));",
        "question": "What are the products with 5% tax?",
        "sql_query": "SELECT id, Name, Tax FROM Goods WHERE Tax = 5;",
        "reason": "Tax column is explicit; semantic search not required.",
    },
]

GENERATE_OR_CORRECT_SQL_STATEMENT_PREFIX = """
# SYSTEM INSTRUCTIONS
You are a PostgresSQL expert that generates a valid SQL query based on a natural language question and the relevant tables with the schema.

## Instructions:
- DECIDE IF THE QUERY REQUIRES SEMANTIC CALCULATIONS OR STANDARD SQL.
- USE ONLY the <=> function for text similarity searches. Never use LIKE or ILIKE.
- **FOR CONDITIONS BASED ON COLUMNS PREFIXED WITH `usevec_[column_name]`, ENSURE THE EMBEDDINGS COLUMN `useembed_[column_name]` IS USED IN VECTOR SIMILARITY CALCULATIONS.**
- DO NOT READ embeddings columns, ONLY USE THEM for VECTOR SIMILARITY CALCULATIONS.
- use only the keywords **(embedding, k) as placeholders** in the SQL query to replace the embedding and k values.
- ALWAYS READ THE **ID AND DESCRIPTION** COLUMNS THAT PROVIDES INFORMATION ABOUT THE FETCHED RESULTS.**
- **ALWAYS ORDER THE FETCHED RESULTS BY THE SIMILARITY SCORE.**

## Examples:""".strip()

FEW_SHOT_PROMPT_TEMPLATE = "### Example:\n```\nTable info: {table}\nQuestion: {question}\nSQL query: {sql_query}\nReason: {reason}\n```\n".strip()

PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_SYS = FewShotPromptTemplate(
    example_prompt=PromptTemplate.from_template(FEW_SHOT_PROMPT_TEMPLATE),
    examples=SQL_QUERY_FEW_SHOT_EXAMPLES,
    prefix=GENERATE_OR_CORRECT_SQL_STATEMENT_PREFIX,
    suffix="",
    input_variables=["table", "question", "sql_query"],
)

GENERATE_RESPONSE_FROM_SQL = """
# Task: Response generation from Table
You are the last state of a text-to-SQL system. You have to generate a response based on the user query, generated query results. 
Do not use any information other than the user query and the generated query results.

### SQL query results:
{query_results}

### Question: {user_query}
""".strip()

PROMPT_GENERATE_RESPONSE_FROM_SQL = PromptTemplate.from_template(
    GENERATE_RESPONSE_FROM_SQL
)

GENERATE_OR_CORRECT_SQL_STATEMENT = """
# SQL Query Generation Task
- Generate the PostgresSQL query based on the table schema given below for the Question.
- If the table contains a column says Description ensure that it is included in the query
- Your task also involves correcting any previously generated SQL query.
- If the previous query is empty, it means this is your first time generating the query.
- CONVERT THE REQUIRED COLUMNS INTO SUITABLE TYPES such as decimal for numeric value operations.

{all_tables}


### Previous SQL query:   
   {generated_query}
### Previous SQL query error: 
   {query_error}

### Format Instructions:
   {format_instructions}

### Question: {user_query}
""".strip()

PROMPT_GENERATE_OR_CORRECT_SQL_STATEMENT_HUMAN = PromptTemplate.from_template(
    GENERATE_OR_CORRECT_SQL_STATEMENT,
    partial_variables={
        "format_instructions": sql_queries_output_parser.get_format_instructions()
    },
)

GET_THE_CORE_SUBJECT = """
You are a helpful system that extracts the **core subject or concept** from a natural language query. 
Remove any questioning phrases, specific details (e.g., prices, quantities), and extra qualifiers. 
Your goal is to isolate the **main category, topic, or entity group** that reflects the essence of the query—this will be used for semantic (KNN vector) search.

Focus on:
- The central entities or categories mentioned.
- Generalizing specific examples where possible.
- Removing modifiers that do not change the core meaning.

### Examples:
Input: "What is the average CGST price of dairy products like milk, lassi, butter, etc?"
Output: "dairy like milk lassi butter"

Input: "Get me all the information on fruits"
Output: "fruits"

Input: "What are the places near to river banks?"
Output: "places near river banks"

Input: "Could you tell me the best methods to cook pasta, including spaghetti and penne?"
Output: "cook pasta spaghetti and penne"

Input: "What are the products related to Caffeine and also give wooden products?"
OUtput: "Caffeine products wooden products"


### Now process the following query:
Input: {user_query}
Output:
"""

PROMPT_GET_THE_CORE_SUBJECT = PromptTemplate.from_template(GET_THE_CORE_SUBJECT)

GET_REQUIRED_TABLES = """
# SYSTEM INSTRUCTIONS
You are a part of Text-to-SQL system. You will be given a list of tables and their descriptions.
Your task is to analyze a natural language question and identify the relevant tables.
The selected tables will be used in the next step to generate the SQL query. 
Focus only on identifying tables that are necessary and directly related to the question.

### Tables with descriptions:
{table_descriptions}

### Format Instructions:
{format_instructions}

### Question: {user_query}
"""

PROMPT_GET_REQUIRED_TABLES = PromptTemplate.from_template(
    GET_REQUIRED_TABLES,
    partial_variables={
        "format_instructions": table_names_output_parser.get_format_instructions()
    },
)
