def make_citation(chunk):
    return {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "source": chunk.source,
        "filename": chunk.filename,
        "page": chunk.page,
        "section": chunk.section,
        "date": chunk.date,
        "version": chunk.version,
    }

def citations_for(chunks):
    return [make_citation(c) for c in chunks]
