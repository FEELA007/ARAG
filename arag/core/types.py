from dataclasses import dataclass, field
from typing import Any

@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    source: str
    filename: str
    page: int | None = None
    section: str | None = None
    date: str | None = None
    version: str | None = None
    chunk_index: int = 0
    permissions: list[str] = field(default_factory=lambda: ["public"])
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class RetrievalResult:
    chunk: Chunk
    score: float
    rank: int
    strategy: str
    rerank_score: float | None = None

@dataclass
class QueryResult:
    answer: str
    status: str
    strategy: str
    confidence: float
    citations: list[dict[str, Any]]
    retrieved: list[RetrievalResult]
    diagnostics: dict[str, Any] = field(default_factory=dict)
