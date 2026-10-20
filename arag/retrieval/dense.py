from sentence_transformers import SentenceTransformer
import numpy as np

class DenseRetriever:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embeddings = None
        self.chunks = []

    def build(self, chunks):
        self.chunks = chunks
        self.embeddings = self.model.encode(
            [c.text for c in chunks],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return self.embeddings

    def search(self, query: str, top_k: int = 8):
        if self.embeddings is None:
            raise RuntimeError("Dense index has not been built")
        q = self.model.encode([query], normalize_embeddings=True)[0]
        scores = np.asarray(self.embeddings) @ q
        indices = np.argsort(-scores)[:top_k]
        return [(int(i), float(scores[i])) for i in indices]
