# ARAG Advanced — three-tier local RAG system

This project follows the uploaded **ARAG System Architecture** presentation: document extraction and chunking, embeddings, dense/vector retrieval, BM25 keyword retrieval, reciprocal-rank fusion (RRF), optional cross-encoder reranking, evidence sufficiency checks, grounded generation, and source provenance.

## Important accuracy note

The 75%, 85%, and 95% values are **target accuracy levels**, not results or guarantees. Do not report them as measured accuracy until all three configurations are evaluated against the same labelled benchmark. Use `eval_questions_template.csv` and include unanswerable questions.

## Three tiers

| Tier | Target (unverified) | Document limit | Retrieval configuration | Context token cap | Output token cap |
|---|---:|---:|---|---:|---:|
| ARAG Lite / Model 1 | 75% | 1 document | `all-MiniLM-L6-v2` dense retrieval | 1,000 | 128 |
| ARAG Balanced / Model 2 | 85% | Up to 4 documents | BGE-small embeddings + BM25 + RRF | 4,000 | 256 |
| ARAG Advanced / Model 3 | 95% | Up to 10 documents | GTE-small + multi-query hybrid retrieval + RRF + cross-encoder reranking + evidence check | 32,000 | 512 |

All tiers use the same local Hugging Face generation model by default (`Qwen/Qwen2.5-1.5B-Instruct`) so the main experimental differences are retrieval and evidence selection. Change `ARAG_GENERATOR_MODEL` to use a compatible locally runnable causal language model with an appropriate context window. Models are downloaded from Hugging Face and run in the local Python process; no paid inference API is used.

Each uploaded file must be PDF, DOCX, or TXT and no larger than 10 MB. Document count depends on the selected tier. The global evidence-context budget starts at 10,000 tokens and is configurable from 1,000 to 32,000 in the UI; the selected tier's cap still applies. Output token limits are tier-specific.

## Run on Windows / PowerShell

Open a terminal **in the folder containing `requirements-low.txt`, `backend`, `frontend`, and `arag`**.

### 1. Create a virtual environment

```powershell
py -m venv .venv
```

### 2. Install dependencies (no PowerShell activation needed)

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-low.txt
```

If your virtual environment is in the parent folder instead, use `..\.venv\Scripts\python.exe` in both commands.

### 3. Start the API and UI

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

If `.venv` is in the parent folder:

```powershell
..\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. Do not open `frontend/index.html` directly; the API serves the UI and its `/api/*` endpoints.

## First-run notes

- The first model run downloads the selected embedding model, cross-encoder (Model 3), and the shared Qwen generator. Downloads can be several GB and require internet access, disk space, and adequate RAM. CPU inference may be slow; a CUDA GPU is used automatically if PyTorch detects one.
- Model downloads are lazy: embedding/reranker/generator weights load only when a query needs them.
- If Qwen cannot load because of memory or dependency issues, the API returns the retrieved evidence as an explicitly labelled fallback and surfaces a warning. This fallback is not a generated answer.
- A scanned PDF without an OCR text layer may produce no chunks. Run OCR first if needed.
- Sessions, indexes, and caches are in memory for this local MVP. Restarting the backend clears them, so upload documents again.
- This is a local single-user prototype. Do not expose it publicly without authentication, upload scanning, resource limits, access controls, persistent storage, and security review.

## API

- `GET /api/health` — health status
- `GET /api/config` — tier settings and budget range
- `POST /api/upload` — multipart fields `files` (repeat for each document) and `model`
- `POST /api/query` — JSON `{ "document_id": "...", "question": "...", "model": "model_1", "token_budget": 10000 }`

## Evaluation

Use the same documents and same labelled questions for all three tiers. Record answer correctness, faithfulness, citation correctness, Recall@K / MRR / NDCG where relevant, latency, memory, and abstention quality. For a credible comparison, use at least 30–50 verified questions as described in the architecture presentation. Accuracy values should be filled in only after evaluation.
