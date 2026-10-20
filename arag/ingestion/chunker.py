def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            boundaries = [
                text.rfind("\n\n", start, end),
                text.rfind(". ", start, end),
                text.rfind(" ", start, end),
            ]
            boundary = max(boundaries)
            if boundary > start:
                end = boundary + 1

        part = text[start:end].strip()
        if part:
            chunks.append(part)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks
