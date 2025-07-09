from typing import List

from sentence_transformers import SentenceTransformer

from embedder.base import BaseEmbedder, batch_list


class SentenceTransformerEmbedder(BaseEmbedder):
    def __init__(self, model: str) -> None:
        self.client = SentenceTransformer(model)
        self.model = model

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.client.encode(texts)
        # convert into float
        embeddings = embeddings.tolist()
        return embeddings

    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        embeddings = []

        input_batches = list(batch_list(chunks))

        for batch in input_batches:
            embeddings.extend(self.embed_texts(batch))

        return embeddings

    def get_dim(self):
        return self.client.get_sentence_embedding_dimension()
