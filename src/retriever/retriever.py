import json
from decimal import Decimal
from typing import Dict, List

from config import settings
from database.connection import PGConnection
from embedder.openai_embedder import AzureOpenAIEmbedder


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# Retrieves data from the database, when the user queries something
# invoked by the execute_query node
class PGRetriever:
    def __init__(self):
        self.db_path = settings.POSTGRES_DSN.unicode_string()
        self.k = 10

    def get_relevant_documents(
        self,
        query: str,
        user_query: str,
    ) -> List[Dict]:
        embedder = AzureOpenAIEmbedder()
        user_query_embedding = embedder.embed_texts([user_query])[0]

        # Connect to PostgreSQL
        c = PGConnection(self.db_path)
        conn = c.get_conn()

        try:
            # Prepare SQL and parameters
            params = {
                "embedding": (
                    json.dumps(user_query_embedding) if "embedding" in query else None
                ),
                "query": user_query if "query" in query else None,
                "k": self.k if "k" in query else self.k,
            }

            with conn.cursor() as cur:
                cur.execute(query, params)
                colnames = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
                parsed_rows = [dict(zip(colnames, row)) for row in rows]

            return parsed_rows
        except Exception as e:
            raise e
        finally:
            conn.close()
