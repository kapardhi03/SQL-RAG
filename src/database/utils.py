from typing import List

from langchain_core.prompts import PromptTemplate
from psycopg2.extensions import cursor


# gets all the table names in the database
def get_tables(cursor: cursor) -> List[str]:
    cursor.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )
    tables = cursor.fetchall()
    return [table[0] for table in tables if table[0] != "description_table"]


# Gets the schema (column information) of a specific table
def get_columns(cursor: cursor, table_name: str) -> List[str]:
    cursor.execute(
        f"""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}';
    """
    )
    columns = cursor.fetchall()

    return [
        column[0] for column in columns if column[1] == "text" or column[1] == "varchar"
    ]


# Generates a sample with schema information and k rows from the table
# this helps the LLM to understand what and how the table store something
def get_sample(cursor: cursor, table_name: str, limit: int = 5) -> str:
    # Get schema info and filter out columns starting with 'useembed_'
    cursor.execute(
        """
        SELECT 
            column_name, 
            data_type, 
            is_nullable, 
            column_default
        FROM 
            information_schema.columns
        WHERE 
            table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table_name,),
    )
    schema_rows = cursor.fetchall()
    schema_rows = [row for row in schema_rows if not row[0].startswith("useembed_")]

    # Build markdown schema
    schema_md = f"## Schema of table `{table_name}`\n\n"
    schema_md += "| Column Name | Data Type | Is Nullable | Default |\n"
    schema_md += "|-------------|-----------|-------------|---------|\n"
    for col in schema_rows:
        schema_md += "| {} | {} | {} | {} |\n".format(
            *[c if c is not None else "" for c in col]
        )

    # Get sample data and filter out vector columns
    all_column_names = [row[0] for row in schema_rows]  # only non-vector columns
    col_list_sql = ", ".join(f'"{col}"' for col in all_column_names)

    cursor.execute(f'SELECT {col_list_sql} FROM "{table_name}" LIMIT %s;', (limit,))
    sample_rows = cursor.fetchall()

    data_md = f"\n## Markdown version of first {limit} rows\n\n"
    data_md += "| " + " | ".join(all_column_names) + " |\n"
    data_md += "| " + " | ".join(["---"] * len(all_column_names)) + " |\n"
    for row in sample_rows:
        data_md += (
            "| " + " | ".join([str(r) if r is not None else "" for r in row]) + " |\n"
        )

    return schema_md + data_md


GET_TABLE_DESCRIPTION = """
# SYSTEM INSTRUCTIONS
You are the first state of a text-to-SQL system. You have to generate a description for the table.
Generate a description based on the table schema and sample rows. that will be later used to figure out
which tables to use in the SQL query. **Ignore any vector representing columns for now.**

### Table Name:
{table_name}

{table_sample}

### Output Instructions:
- **Output must ONLY be a text description of the table with no other explanation.**
"""
PROMPT_GET_TABLE_DESCRIPTION = PromptTemplate.from_template(
    GET_TABLE_DESCRIPTION,
)
