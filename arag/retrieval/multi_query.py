def generate_query_variants(query: str) -> list[str]:
    # Lightweight deterministic baseline. Replace with an LLM/query-expander later.
    variants = [query]
    lowered = query.lower().strip()

    if lowered.startswith("what is "):
        variants.append(lowered.replace("what is ", "", 1))
    elif lowered.startswith("how does "):
        variants.append(lowered.replace("how does ", "", 1))

    return list(dict.fromkeys(variants))

def multi_query_search(query, search_fn, top_k=6):
    variants = generate_query_variants(query)
    merged = []
    seen = set()

    for variant in variants:
        for item in search_fn(variant, top_k):
            if item[0] not in seen:
                seen.add(item[0])
                merged.append(item)

    return merged[:top_k]
