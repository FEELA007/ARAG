from arag.retrieval.rrf import reciprocal_rank_fusion


class HybridRetriever:
    def __init__(self, dense, bm25, rrf_k=60):
        self.dense = dense
        self.bm25 = bm25
        self.rrf_k = rrf_k

    def search(self, query, top_k=6):
        dense = self.dense.search(query, top_k)
        lexical = self.bm25.search(query, top_k)
        fused = reciprocal_rank_fusion(
            [[i for i, _ in dense], [i for i, _ in lexical]],
            self.rrf_k,
        )
        return [(i, score) for i, score in fused[:top_k]]
