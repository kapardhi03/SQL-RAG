from typing import List


def batch_list(input_list, batch_size=2048):
    for i in range(0, len(input_list), batch_size):
        yield input_list[i : i + batch_size]


class BaseEmbedder:
    def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
        pass

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        pass
