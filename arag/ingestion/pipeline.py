from pathlib import Path
import json
from datetime import datetime, timezone

from arag.core.types import Chunk
from arag.ingestion.cleaner import clean_text
from arag.ingestion.chunker import chunk_text
from arag.ingestion.extractors import extract_pages, SUPPORTED
from arag.ingestion.versioning import document_id, chunk_id

def ingest_document(path: str | Path, chunk_size=1000, overlap=150) -> list[Chunk]:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported document: {path}")

    doc_id = document_id(path)
    version = doc_id[:12]
    ingested_at = datetime.now(timezone.utc).isoformat()
    result = []

    for page, raw in extract_pages(path):
        cleaned = clean_text(raw)
        if not cleaned:
            continue

        for index, text in enumerate(chunk_text(cleaned, chunk_size, overlap)):
            cid = chunk_id(doc_id, page, index, text)
            result.append(
                Chunk(
                    chunk_id=cid,
                    document_id=doc_id,
                    text=text,
                    source=str(path),
                    filename=path.name,
                    page=page,
                    version=version,
                    chunk_index=index,
                    metadata={"ingested_at": ingested_at},
                )
            )
    return result

def ingest_directory(raw_dir: str | Path, output: str | Path, chunk_size=1000, overlap=150) -> list[Chunk]:
    raw_dir = Path(raw_dir)
    all_chunks = []

    for path in sorted(raw_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            all_chunks.extend(ingest_document(path, chunk_size, overlap))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk.__dict__, ensure_ascii=False) + "\n")

    return all_chunks

def load_chunks(path: str | Path) -> list[Chunk]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(Chunk(**json.loads(line)))
    return chunks
