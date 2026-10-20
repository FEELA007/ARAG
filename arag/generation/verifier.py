from arag.core.answer import evidence_confidence

def verify_answer(answer: str, chunks) -> dict:
    if not answer or not chunks:
        return {"supported": False, "confidence": 0.0, "reason": "No answer/evidence"}

    answer_terms = set(answer.lower().split())
    evidence_terms = set(" ".join(c.text for c in chunks).lower().split())
    overlap = len(answer_terms & evidence_terms) / max(1, len(answer_terms))

    return {
        "supported": overlap >= 0.30,
        "confidence": round(min(1.0, overlap), 4),
        "reason": "Lexical evidence coverage baseline",
    }
