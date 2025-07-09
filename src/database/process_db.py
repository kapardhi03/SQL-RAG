import json
from typing import List

from langchain_core.messages import HumanMessage
from psycopg2.extensions import connection, cursor

from agents.models import models
from config import settings
from database.connection import PGConnection
from database.utils import (
    PROMPT_GET_TABLE_DESCRIPTION,
    get_columns,
    get_sample,
    get_tables,
)
from embedder.openai_embedder import AzureOpenAIEmbedder


# Given the sample data of a table, this generates a description of the table using an LLM
def get_table_description(table_name: str, sample: str):
    model = models["azure-gpt-4o"]

    prompt = PROMPT_GET_TABLE_DESCRIPTION.format(
        table_name=table_name,
        table_sample=sample,
    )

    messages = [HumanMessage(content=prompt)]

    response = model.invoke(messages)

    return response.content


# The chosen text columns will be embedding into vectors and will be inserted into a new corresponding column
# The existing columns will be renamed to usevec_[col] and the new column will be useembed_[col]
def embedd_text_columns_and_add_description(
    conn: connection, cursor: cursor, table_name: str, columns: List[str]
) -> None:
    embedder = AzureOpenAIEmbedder()

    for column in columns:
        cursor.execute(f"SELECT id, {column} FROM {table_name};")
        rows = cursor.fetchall()  # List of tuples: (id, column_value)

        ids = [row[0] for row in rows]
        column_values = [row[1] for row in rows]

        try:
            embeddings = embedder.embed_chunks(column_values)
        except Exception as e:
            print(f"Failed to embed column {column}: {e}")
            continue

        # Rename the original column
        cursor.execute(
            f"""
            ALTER TABLE {table_name} RENAME {column} TO usevec_{column};
        """
        )

        # Add a new column for the embedding
        cursor.execute(
            f"""
            ALTER TABLE {table_name} ADD COLUMN useembed_{column} vector({embedder.get_dim()});
        """
        )

        # Update the embedding column row by row using the ID
        for row_id, embedding in zip(ids, embeddings):
            cursor.execute(
                f"""
                UPDATE {table_name}
                SET useembed_{column} = %s
                WHERE id = %s;
            """,
                (json.dumps(embedding), row_id),
            )

        print()
        print(f"For column: {column}")
        print(f"Changed column name to usevec_{column}")
        print(
            f"Updated {len(embeddings)} rows with embeddings for column useembed_{column}"
        )
        print()

    table_sample = get_sample(cursor, table_name)
    table_description = get_table_description(table_name, table_sample)

    cursor.execute(
        f"""
        INSERT INTO description_table (t_name, description) 
        VALUES ('{table_name}', '{table_description}');
    """
    )

    conn.commit()


# Iterates through all the tables and embeds the necessary text columns
def process_db() -> None:
    c = PGConnection(settings.POSTGRES_DSN.unicode_string())
    conn = c.get_conn()
    cursor = conn.cursor()

    tables = get_tables(cursor)

    for table in tables:
        columns = get_columns(cursor, table)
        print("Table name: ", table)
        print("Text columns: ", ", ".join(columns))

        print("Enter the columns to embed: (Space separated)")
        columns_to_embed = input().split(", ")

        embedd_text_columns_and_add_description(conn, cursor, table, columns_to_embed)
        print("----DONE----")
        print()


if __name__ == "__main__":
    process_db()
