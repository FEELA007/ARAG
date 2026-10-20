from arag.ingestion.cleaner import clean_text

def test_cleaner():
    value = clean_text(" hello   world \r\n\r\n\r\n test ")
    assert value == "hello world\n\ntest"
