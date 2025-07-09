from typing import List, Literal

from google import genai
from google.genai import types

from embedder.base import BaseEmbedder, batch_list


class GeminiEmbedder(BaseEmbedder):
    def __init__(
        self,
        model: str,
        mode: Literal[
            "RETRIEVAL_DOCUMENT", "SEMANTIC_SIMILARITY"
        ] = "SEMANTIC_SIMILARITY",
    ) -> None:
        self.client = genai.Client()
        self.model = model
        self.mode = mode

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        texts = [str(i) for i in texts]

        embedding_response = self.client.models.embed_content(
            contents=texts,
            model=self.model,
            config=types.EmbedContentConfig(task_type=self.mode),
        )

        embeddings = []
        for embedding in embedding_response.embeddings:
            embeddings.append(embedding.values)

        return embeddings

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        embeddings = []

        input_batches = list(batch_list(chunks, batch_size=100))

        for batch in input_batches:
            embeddings.extend(self.embed_texts(batch))

        return embeddings

    def get_dim(self):
        return 768
