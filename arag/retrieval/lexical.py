from rank_bm25 import BM25Okapi


class BM25Retriever:
    def __init__(self):
        self.chunks = []
        self.index = None

    def build(self, chunks):
        self.chunks = chunks
        tokenized = [chunk.text.lower().split() for chunk in chunks]
        self.index = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 8):
        if self.index is None:
            raise RuntimeError("BM25 index has not been built")
        scores = self.index.get_scores(query.lower().split())
        indices = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )[:top_k]
        return [(i, float(scores[i])) for i in indices]
