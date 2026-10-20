from arag.ingestion.chunker import chunk_text

def test_chunker():
    text = "word " * 1000
    chunks = chunk_text(text, 100, 20)
    assert chunks
    assert all(chunks)

def test_invalid_overlap():
    try:
        chunk_text("abc", 10, 10)
        assert False
    except ValueError:
        assert True
