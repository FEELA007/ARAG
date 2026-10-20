from pathlib import Path
from pypdf import PdfReader
from docx import Document

SUPPORTED = {".pdf", ".docx", ".txt"}

def extract_pages(path: Path) -> list[tuple[int, str]]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        reader = PdfReader(str(path))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]

    if ext == ".docx":
        doc = Document(str(path))
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        return [(1, "\n".join(parts))]

    if ext == ".txt":
        return [(1, path.read_text(encoding="utf-8", errors="replace"))]

    raise ValueError(f"Unsupported file type: {ext}")
