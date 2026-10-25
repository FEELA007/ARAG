class CrossEncoderReranker:
    def __init__(self, model_name: str):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(self, query, chunks, top_k=5):
        pairs = [(query, c.text) for c in chunks]
        scores = self.model.predict(pairs)
        ranked = sorted(
            zip(chunks, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        return [(chunk, float(score)) for chunk, score in ranked[:top_k]]
