import time
from arag.evaluation.metrics import precision_at_k, recall_at_k, reciprocal_rank, ndcg_at_k

def evaluate_retrieval(retriever, dataset, k=5):
    rows = []
    for item in dataset:
        start = time.perf_counter()
        results = retriever.search(item["query"], k)
        latency = time.perf_counter() - start
        ids = [i for i, _ in results]
        relevant = item.get("relevant_ids", [])

        rows.append({
            "query": item["query"],
            "precision_at_k": precision_at_k(ids, relevant, k),
            "recall_at_k": recall_at_k(ids, relevant, k),
            "mrr": reciprocal_rank(ids, relevant),
            "ndcg": ndcg_at_k(ids, relevant, k),
            "latency_ms": latency * 1000,
        })
    return rows
