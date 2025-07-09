from typing import List

from openai import AzureOpenAI, OpenAI

from config import settings
from embedder.base import BaseEmbedder, batch_list


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model: str) -> None:
        self.client = OpenAI()
        self.model = model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embedding_response = self.client.embeddings.create(
            input=texts, model=self.model
        )

        embeddings = []
        for embedding in embedding_response.data:
            embeddings.append(embedding.embedding)

        return embeddings

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        embeddings = []

        chunks = [i if i else "N/A" for i in chunks]

        input_batches = list(batch_list(chunks))

        for batch in input_batches:
            embeddings.extend(self.embed_texts(batch))

        return embeddings

    def get_dim(self):
        return 1536


class AzureOpenAIEmbedder(BaseEmbedder):
    def __init__(self, model="text-embedding-3-small") -> None:
        self.client = AzureOpenAI(
            api_version="2025-01-01-preview",
            azure_endpoint=settings.AZURE_GPT_ENDPOINT,
            api_key=settings.AZURE_GPT_KEY,
        )
        self.model = model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embedding_response = self.client.embeddings.create(
            input=texts, model=self.model
        )

        embeddings = []
        for embedding in embedding_response.data:
            embeddings.append(embedding.embedding)

        return embeddings

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        embeddings = []

        chunks = [i if i else "N/A" for i in chunks]

        input_batches = list(batch_list(chunks))

        for batch in input_batches:
            embeddings.extend(self.embed_texts(batch))

        return embeddings

    def get_dim(self):
        return 1536
