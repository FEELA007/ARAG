from arag.retrieval.multi_query import multi_query_search

def query_decompose(query: str) -> list[str]:
    # Baseline decomposition for compound questions.
    separators = [" and ", " then ", ";"]
    for sep in separators:
        parts = [p.strip() for p in query.split(sep) if p.strip()]
        if len(parts) > 1:
            return parts
    return [query]

def corrective_retrieve(query, search_fn, top_k=6):
    results = search_fn(query, top_k)
    if not results:
        return {"grade": "BAD", "results": []}

    scores = [score for _, score in results]
    best = max(scores)

    if best >= 0.75:
        grade = "GOOD"
    elif best >= 0.45:
        grade = "PARTIAL"
    else:
        grade = "BAD"

    return {"grade": grade, "results": results}
