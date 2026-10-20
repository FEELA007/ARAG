class LocalGenerator:
    def __init__(self, model_name: str, max_new_tokens=256, temperature=0.0):
        from transformers import pipeline
        self.pipe = pipeline("text2text-generation", model=model_name)
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

    def generate(self, query: str, chunks):
        context = "\n\n".join(
            f"[{i+1}] {c.text}" for i, c in enumerate(chunks)
        )
        prompt = (
            "Answer the question using only the supplied evidence. "
            "If the evidence is insufficient, say so.\n\n"
            f"Evidence:\n{context}\n\nQuestion: {query}\nAnswer:"
        )
        output = self.pipe(
            prompt,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )[0]["generated_text"]
        return output.strip()

class ExtractiveGenerator:
    def generate(self, query: str, chunks):
        if not chunks:
            return "I could not find sufficient evidence in the knowledge base."

        query_terms = set(query.lower().split())
        scored = []
        for chunk in chunks:
            terms = set(chunk.text.lower().split())
            overlap = len(query_terms & terms)
            scored.append((overlap, chunk.text))

        scored.sort(reverse=True)
        return scored[0][1]
