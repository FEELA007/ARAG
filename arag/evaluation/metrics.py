import math


def precision_at_k(retrieved, relevant_ids, k):
    ids = [x for x in retrieved[:k]]
    return sum(i in relevant_ids for i in ids) / max(1, k)


def recall_at_k(retrieved, relevant_ids, k):
    if not relevant_ids:
        return 0.0
    ids = set(retrieved[:k])
    return len(ids & set(relevant_ids)) / len(set(relevant_ids))


def reciprocal_rank(retrieved, relevant_ids):
    relevant_ids = set(relevant_ids)
    for rank, item in enumerate(retrieved, 1):
        if item in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved, relevant_ids, k):
    relevant = set(relevant_ids)
    dcg = sum(
        (1.0 if item in relevant else 0.0) / math.log2(rank + 1)
        for rank, item in enumerate(retrieved[:k], 1)
    )
    ideal_hits = min(k, len(relevant))
    idcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return dcg / idcg if idcg else 0.0
