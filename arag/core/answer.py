def evidence_confidence(results):
    if not results:
        return 0.0
    scores = [max(0.0, float(r.score)) for r in results]
    # Conservative baseline confidence.
    return min(1.0, max(scores) if scores else 0.0)


def answerability(results, threshold=0.35):
    if not results:
        return "retrieval_failed"
    confidence = evidence_confidence(results)
    if confidence < threshold:
        return "insufficient_evidence"
    return "answerable"


def detect_conflict(chunks):
    # Lightweight lexical conflict heuristic; intended as a baseline.
    dates = [c.date for c in chunks if c.date]
    versions = [c.version for c in chunks if c.version]
    if len(set(dates)) > 1 or len(set(versions)) > 1:
        return True
    return False
