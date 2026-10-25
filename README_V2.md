# ARAG v2 — Adaptive, Reliable & Cost-Aware RAG

This version is based on the supplied ARAG project source and architecture presentation.

## Included in this version
- Three retrieval tiers with different embedding models and resource limits:
  - Lite: `sentence-transformers/all-MiniLM-L6-v2` (dense retrieval)
  - Balanced: `BAAI/bge-small-en-v1.5` (dense + BM25 + RRF)
  - Advanced: `thenlper/gte-small` (multi-query hybrid retrieval + RRF + cross-encoder reranking)
- Configurable Advanced cross-encoder via `ARAG_RERANKER_MODEL`; default is `cross-encoder/ms-marco-MiniLM-L-6-v2`.
- One controlled corrective pass for Advanced when the first retrieval pass fails the evidence heuristic.
- Grounded local generation with `Qwen/Qwen2.5-1.5B-Instruct` by default.
- Evidence/source panel with dense, BM25, RRF and reranker signals.
- Indexed file inventory and a per-query retrieval pipeline trace.
- CUDA is used automatically by the generator when the installed PyTorch build supports it.
- Local browser UI with document chat, sources, retrieval metrics, settings and help.

## Run on Windows / PowerShell
From the project folder:
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-low.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000`. API documentation is at `http://127.0.0.1:8000/docs`.

## Model selection / experimentation
The embedding models and tier strategy are defined in `backend/app.py`. To test another compatible cross-encoder for Advanced, set an environment variable before starting the server, for example:
```powershell
$env:ARAG_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```
The architecture presentation names BERT-, RoBERTa-, and DeBERTa-family reranker comparisons but does not specify frozen checkpoints for all three families. Choose compatible relevance-scoring checkpoints and benchmark them on the same labelled set before making comparative claims.

## Accuracy and limitations
- The 75%, 85%, and 95% values are **targets**, not measured accuracy.
- The evidence sufficiency check is a lightweight heuristic, not a calibrated confidence model.
- Corrective retrieval is a single bounded retry, not a guarantee that missing evidence will be found.
- The UI's pipeline trace reports implemented stages and statuses; it is not a substitute for benchmark evaluation.
- This remains a local, single-user prototype. Sessions and indexes are in memory and reset on restart. The UI is not an authentication or authorization boundary. Do not expose it publicly without implementing server-side authentication, document ACL enforcement, persistent storage, upload scanning and security review.
- First model use may download weights from Hugging Face and can take time. Internet access is required for initial downloads unless the weights are already cached.
