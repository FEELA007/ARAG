import hashlib
import json
from pathlib import Path

class SemanticCache:
    # Baseline exact-normalized cache. Embedding similarity can be added without changing the API.
    def __init__(self, path="data/index/cache.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    @staticmethod
    def key(query: str) -> str:
        normalized = " ".join(query.lower().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get(self, query):
        return self.data.get(self.key(query))

    def set(self, query, value):
        self.data[self.key(query)] = value
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
