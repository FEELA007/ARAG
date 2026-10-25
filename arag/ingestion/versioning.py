import hashlib
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def document_id(path: Path) -> str:
    return file_hash(path)


def chunk_id(
    document_id_value: str,
    page: int | None,
    index: int,
    text: str,
) -> str:
    raw = f"{document_id_value}:{page}:{index}:{text}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
