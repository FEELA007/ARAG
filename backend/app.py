from __future__ import annotations

import os
import re
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from arag.ingestion.pipeline import ingest_document

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
UPLOAD_DIR = ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_BYTES = 10 * 1024 * 1024
DEFAULT_TOKEN_BUDGET = 10_000
MIN_TOKEN_BUDGET = 1_000
MAX_TOKEN_BUDGET = 32_000
GENERATOR_MODEL = os.getenv("ARAG_GENERATOR_MODEL", "Qwen/Qwen2.5-1.5B-Instruct")

# Accuracy values are research targets, not promises. Measure them on a
# consistent labelled test set.
TIERS: dict[str, dict[str, Any]] = {
    "model_1": {
        "name": "ARAG Lite",
        "target_accuracy": 75,
        "max_files": 1,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "retrieval": "dense",
        "candidate_k": 4,
        "final_k": 3,
        "context_cap": 1_000,
        "output_tokens": 128,
        "reranker_model": None,
        "description": "Dense semantic retrieval · low compute · one document",
    },
    "model_2": {
        "name": "ARAG Balanced",
        "target_accuracy": 85,
        "max_files": 4,
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "retrieval": "hybrid",
        "candidate_k": 10,
        "final_k": 5,
        "context_cap": 4_000,
        "output_tokens": 256,
        "reranker_model": None,
        "description": "BGE embeddings · BM25 · reciprocal-rank fusion · up to four documents",
    },
    "model_3": {
        "name": "ARAG Advanced",
        "target_accuracy": 95,
        "max_files": 10,
        "embedding_model": "thenlper/gte-small",
        "retrieval": "hybrid_rerank",
        "candidate_k": 18,
        "final_k": 7,
        "context_cap": 32_000,
        "output_tokens": 512,
        "reranker_model": os.getenv(
            "ARAG_RERANKER_MODEL",
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
        ),
        "description": (
            "GTE embeddings · multi-query hybrid retrieval · "
            "cross-encoder reranking · evidence check"
        ),
    },
}

app = FastAPI(title="ARAG Advanced API", version="1.0.0")
# Single-user/local prototype: sessions and indexes are in memory and reset on restart.
SESSIONS: dict[str, dict[str, Any]] = {}
_EMBEDDERS: dict[str, SentenceTransformer] = {}
_RERANKERS: dict[str, Any] = {}
_GENERATOR: Any = None
_GENERATOR_LOAD_ERROR: str | None = None


class QueryRequest(BaseModel):
    document_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=4_000)
    model: str = Field(default="model_1")
    token_budget: int = Field(
        default=DEFAULT_TOKEN_BUDGET,
        ge=MIN_TOKEN_BUDGET,
        le=MAX_TOKEN_BUDGET,
    )


def _tier(model: str) -> dict[str, Any]:
    if model not in TIERS:
        raise HTTPException(status_code=400, detail="Choose model_1, model_2, or model_3.")
    return TIERS[model]


def _get_gpu_metrics() -> dict[str, Any]:
    try:
        import torch

        if not torch.cuda.is_available():
            return {
                "available": False,
                "device": None,
                "allocated_mb": None,
                "reserved_mb": None,
            }
        return {
            "available": True,
            "device": torch.cuda.get_device_name(0),
            "allocated_mb": round(
                torch.cuda.memory_allocated(0) / (1024 ** 2), 2
            ),
            "reserved_mb": round(
                torch.cuda.memory_reserved(0) / (1024 ** 2), 2
            ),
        }
    except Exception:
        return {
            "available": False,
            "device": None,
            "allocated_mb": None,
            "reserved_mb": None,
        }


def _load_embedder(model_name: str) -> SentenceTransformer:
    if model_name not in _EMBEDDERS:
        _EMBEDDERS[model_name] = SentenceTransformer(model_name)
    return _EMBEDDERS[model_name]


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+(?:[-'][a-zA-Z0-9]+)*", text.lower())


def _get_bm25(chunks: list[Any]) -> BM25Okapi:
    # Keep punctuation-normalized tokens for stronger matching of identifiers and terminology.
    return BM25Okapi([_tokens(c.text) or ["__empty__"] for c in chunks])


def _rrf(rankings: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, index in enumerate(ranking, start=1):
            scores[index] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _query_variants(question: str) -> list[str]:
    variants = [question]
    # Lightweight decomposition for conjunction/comparison questions; no external API.
    parts = re.split(
        r"\b(?:and|also|versus|vs\.?|compare|compared with|difference between)\b",
        question,
        flags=re.I,
    )
    for part in parts:
        part = part.strip(" ?.,;:")
        if len(_tokens(part)) >= 3 and part.lower() not in {v.lower() for v in variants}:
            variants.append(part)
    return variants[:4]


def _build_index(
    session: dict[str, Any],
    model: str,
) -> dict[str, Any]:
    cache = session["indexes"]
    if model in cache:
        return cache[model]
    cfg = _tier(model)
    chunks = session["chunks"]
    if not chunks:
        raise HTTPException(
            status_code=422,
            detail=(
                "No text chunks are available. "
                "Re-upload readable documents."
            ),
        )
    embedder = _load_embedder(cfg["embedding_model"])
    vectors = embedder.encode(
        [chunk.text for chunk in chunks],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    index = {
        "chunks": chunks,
        "embedder": embedder,
        "vectors": np.asarray(vectors, dtype=np.float32),
        "bm25": _get_bm25(chunks) if cfg["retrieval"] != "dense" else None,
        "embedding_model": cfg["embedding_model"],
    }
    cache[model] = index
    return index


def _dense_search(
    index: dict[str, Any],
    query: str,
    top_k: int,
) -> list[tuple[int, float]]:
    query_vector = index["embedder"].encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    scores = index["vectors"] @ np.asarray(query_vector, dtype=np.float32)
    return [
        (int(chunk_index), float(scores[chunk_index]))
        for chunk_index in np.argsort(-scores)[:top_k]
    ]


def _lexical_search(
    index: dict[str, Any],
    query: str,
    top_k: int,
) -> list[tuple[int, float]]:
    scores = index["bm25"].get_scores(_tokens(query))
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda chunk_index: float(scores[chunk_index]),
        reverse=True,
    )[:top_k]
    return [
        (int(chunk_index), float(scores[chunk_index]))
        for chunk_index in ranked_indices
    ]


def _get_reranker(model_name: str):
    if model_name not in _RERANKERS:
        from sentence_transformers import CrossEncoder

        _RERANKERS[model_name] = CrossEncoder(model_name)
    return _RERANKERS[model_name]


def _retrieve(
    question: str,
    model: str,
    index: dict[str, Any],
) -> list[dict[str, Any]]:
    cfg = _tier(model)
    chunks = index["chunks"]
    candidate_k = min(cfg["candidate_k"], len(chunks))
    dense = _dense_search(index, question, candidate_k)
    dense_score = {i: score for i, score in dense}
    query_variants = (
        _query_variants(question)
        if cfg["retrieval"] == "hybrid_rerank"
        else [question]
    )

    if cfg["retrieval"] == "dense":
        ranked = [(i, score) for i, score in dense]
        fused_scores = {i: score for i, score in ranked}
    else:
        rankings: list[list[int]] = [[i for i, _ in dense]]
        lexical = _lexical_search(index, question, candidate_k)
        rankings.append([i for i, _ in lexical])
        # Advanced tier fans out a small set of deterministic query views, then fuses all rankings.
        if cfg["retrieval"] == "hybrid_rerank":
            for variant in query_variants[1:]:
                rankings.append([i for i, _ in _dense_search(index, variant, candidate_k)])
                rankings.append([i for i, _ in _lexical_search(index, variant, candidate_k)])
        ranked = _rrf(rankings)
        fused_scores = {i: score for i, score in ranked}

    candidates = [i for i, _ in ranked[:candidate_k]]
    rerank_scores: dict[int, float] = {}
    if cfg["reranker_model"] and candidates:
        reranker = _get_reranker(cfg["reranker_model"])
        pairs = [(question, chunks[i].text) for i in candidates]
        scores = reranker.predict(pairs)
        reranked = sorted(
            zip(candidates, scores),
            key=lambda item: float(item[1]),
            reverse=True,
        )
        rerank_scores = {i: float(score) for i, score in reranked}
        candidates = [i for i, _ in reranked]

    results = []
    for rank, i in enumerate(candidates[:cfg["final_k"]], start=1):
        chunk = chunks[i]
        results.append({
            "index": i,
            "chunk": chunk,
            "rank": rank,
            "score": float(dense_score.get(i, 0.0)),
            "dense_score": float(dense_score.get(i, 0.0)),
            "fusion_score": float(fused_scores.get(i, 0.0)),
            "rerank_score": rerank_scores.get(i),
        })
    return results


def _load_generator():
    global _GENERATOR, _GENERATOR_LOAD_ERROR
    if _GENERATOR is not None:
        return _GENERATOR
    if _GENERATOR_LOAD_ERROR:
        raise RuntimeError(_GENERATOR_LOAD_ERROR)
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(GENERATOR_MODEL)
        model = AutoModelForCausalLM.from_pretrained(GENERATOR_MODEL)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
        _GENERATOR = {
            "tokenizer": tokenizer,
            "model": model,
            "torch": torch,
            "device": device,
        }
        return _GENERATOR
    except Exception as exc:
        _GENERATOR_LOAD_ERROR = (
            f"Could not load local generator '{GENERATOR_MODEL}': {exc}. "
            "Check internet access for the first model download, available "
            "RAM/disk, and installed Transformers/PyTorch versions."
        )
        raise RuntimeError(_GENERATOR_LOAD_ERROR) from exc


def _select_context(
    hits: list[dict[str, Any]],
    token_budget: int,
    tokenizer: Any,
) -> list[dict[str, Any]]:
    selected = []
    used = 0
    for hit in hits:
        text = hit["chunk"].text.strip()
        if not text:
            continue
        token_count = len(tokenizer.encode(text, add_special_tokens=False))
        if token_count > token_budget and not selected:
            ids = tokenizer.encode(text, add_special_tokens=False)[:token_budget]
            hit = dict(hit)
            hit["context_text"] = tokenizer.decode(ids, skip_special_tokens=True)
            hit["context_tokens"] = len(ids)
            selected.append(hit)
            break
        if used + token_count <= token_budget:
            hit = dict(hit)
            hit["context_text"] = text
            hit["context_tokens"] = token_count
            selected.append(hit)
            used += token_count
    return selected


def _generate(
    question: str,
    hits: list[dict[str, Any]],
    model: str,
    user_budget: int,
) -> tuple[str, list[dict[str, Any]], str | None, int]:
    cfg = _tier(model)
    effective_budget = min(user_budget, int(cfg["context_cap"]))
    try:
        gen = _load_generator()
        tokenizer, llm = gen["tokenizer"], gen["model"]
        context_hits = _select_context(hits, effective_budget, tokenizer)
        if not context_hits:
            return (
                "I could not find enough relevant evidence to answer this question "
                "from the uploaded documents.",
                [],
                None,
                0,
            )
        evidence = "\n\n".join(
            (
                f"[S{index}] Source: {hit['chunk'].filename}, "
                f"page {hit['chunk'].page or 'not available'}\n"
                f"{hit.get('context_text', hit['chunk'].text)}"
            )
            for index, hit in enumerate(context_hits, start=1)
        )
        system = (
            "You are ARAG, a helpful, conversational document assistant. "
            "Answer naturally, clearly, and directly, like ChatGPT. "
            "Use the supplied evidence to answer document-related questions. "
            "Never invent facts or present outside knowledge as document content. "
            "If evidence is insufficient, say so. "
            "Explain details when useful, but never dump entire document chunks. "
            "Cite factual claims using source labels such as [S1]. "
            "Use paragraphs or bullets when appropriate. "
            "Return only the answer."
        )
        user = f"""Use only the evidence below to answer the question.

Evidence:
{evidence}

Question: {question}

Give one direct sentence supported by the evidence. Do not add outside facts.
Include the relevant source citation.

Answer:"""
        if getattr(tokenizer, "chat_template", None):
            prompt_ids = tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                tokenize=True,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            )["input_ids"]
        else:
            prompt_ids = tokenizer(
                f"System: {system}\n\nUser: {user}\n\nAssistant:",
                return_tensors="pt",
            )["input_ids"]
        # Leave room for output inside Qwen2.5's 32k context window.
        max_positions = int(getattr(llm.config, "max_position_embeddings", 32768))
        max_input = max(512, max_positions - int(cfg["output_tokens"]) - 64)
        if prompt_ids.shape[-1] > max_input:
            prompt_ids = prompt_ids[:, -max_input:]
        prompt_ids = prompt_ids.to(gen["device"])
        with gen["torch"].inference_mode():
            output = llm.generate(
                input_ids=prompt_ids,
                max_new_tokens=int(cfg["output_tokens"]),
                do_sample=False,
                repetition_penalty=1.05,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated_ids = output[0][prompt_ids.shape[-1]:]
        answer = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        if not answer:
            answer = "I could not produce a grounded answer. Try a more specific question."
        # Keep citations traceable when the generator omits them.
        if context_hits and not re.search(r"\[S\d+\]", answer):
            source_labels = ", ".join(
                f"[S{index}]" for index in range(1, len(context_hits) + 1)
            )
            answer += f"\n\nSources consulted: {source_labels}"
        return answer, context_hits, None, int(prompt_ids.shape[-1])
    except Exception as exc:
        import traceback
        traceback.print_exc()
        # Labeled fallback keeps the demo usable when local generation fails.
        fallback_hits = hits[: min(2, len(hits))]
        if fallback_hits:
            cited_hits = "\n\n".join(
                f"[S{index}] {hit['chunk'].text}"
                for index, hit in enumerate(fallback_hits, start=1)
            )
            fallback = (
                "Generation model unavailable; showing retrieved evidence instead:\n\n"
                f"{cited_hits}"
            )
        else:
            fallback = "I could not find enough relevant evidence to answer this question."
        return fallback, fallback_hits, str(exc), 0


def _evidence_sufficient(question: str, hits: list[dict[str, Any]]) -> bool:
    if not hits:
        return False
    best_dense = max(float(h.get("dense_score", 0.0)) for h in hits)
    q_terms = {t for t in _tokens(question) if len(t) > 2}
    evidence_terms = {t for h in hits for t in _tokens(h["chunk"].text)}
    overlap = len(q_terms & evidence_terms) / max(1, len(q_terms))
    return best_dense >= 0.18 or overlap >= 0.12


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        import torch

        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        cuda_available = bool(torch.cuda.is_available())
    except Exception:
        gpu, cuda_available = None, False
    return {
        "status": "ok",
        "service": "ARAG Advanced API",
        "generator_model": GENERATOR_MODEL,
        "cuda_available": cuda_available,
        "gpu": gpu,
    }


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return {
        "default_token_budget": DEFAULT_TOKEN_BUDGET,
        "min_token_budget": MIN_TOKEN_BUDGET,
        "max_token_budget": MAX_TOKEN_BUDGET,
        "file_size_limit_mb": 10,
        "models": {
            key: {k: v for k, v in cfg.items() if k not in {"reranker_model"}}
            for key, cfg in TIERS.items()
        },
        "accuracy_notice": (
            "75%, 85%, and 95% are target values for evaluation, not measured "
            "or guaranteed accuracy."
        ),
    }


@app.post("/api/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    model: str = Form(default="model_1"),
) -> dict[str, Any]:
    cfg = _tier(model)
    if not files:
        raise HTTPException(status_code=400, detail="Choose at least one document.")
    if len(files) > int(cfg["max_files"]):
        raise HTTPException(
            status_code=413,
            detail=(
                f"{cfg['name']} supports up to {cfg['max_files']} document(s). "
                "Choose another tier or remove files."
            ),
        )

    all_chunks: list[Any] = []
    file_info = []
    total_bytes = 0
    try:
        for uploaded in files:
            filename = Path(uploaded.filename or "document").name
            suffix = Path(filename).suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unsupported file type for '{filename}'. "
                        "Use PDF, DOCX, or TXT."
                    ),
                )
            content = await uploaded.read(MAX_FILE_BYTES + 1)
            if not content:
                raise HTTPException(status_code=400, detail=f"'{filename}' is empty.")
            if len(content) > MAX_FILE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"'{filename}' exceeds the 10 MB per-file limit.",
                )
            total_bytes += len(content)
            temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
            temp_path.write_bytes(content)
            try:
                chunk_size = 700 if model == "model_1" else 850
                overlap = 100 if model == "model_1" else 140
                chunks = ingest_document(
                    temp_path,
                    chunk_size=chunk_size,
                    overlap=overlap,
                )
            finally:
                temp_path.unlink(missing_ok=True)
            for chunk in chunks:
                chunk.filename = filename
                chunk.source = filename
                chunk.metadata = {**(chunk.metadata or {}), "original_filename": filename}
            if not chunks:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"No readable text found in '{filename}'. "
                        "Scanned PDFs may need OCR first."
                    ),
                )
            all_chunks.extend(chunks)
            file_info.append({
                "filename": filename,
                "size_bytes": len(content),
                "chunk_count": len(chunks),
            })

        document_id = uuid.uuid4().hex
        SESSIONS[document_id] = {
            "files": file_info,
            "chunks": all_chunks,
            "indexes": {},
            "created_at": time.time(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document ingestion failed: {exc}") from exc

    return {
        "document_id": document_id,
        "files": file_info,
        "file_count": len(file_info),
        "total_bytes": total_bytes,
        "chunk_count": len(all_chunks),
        "message": f"Indexed {len(file_info)} document(s).",
        "tier": cfg["name"],
    }


@app.post("/api/query")
def query_documents(request: QueryRequest) -> dict[str, Any]:
    cfg = _tier(request.model)
    session = SESSIONS.get(request.document_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=(
                "Document session not found. Re-upload your documents after "
                "restarting the backend."
            ),
        )
    if len(session["files"]) > cfg["max_files"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{cfg['name']} supports up to {cfg['max_files']} document(s), "
                f"but this session has {len(session['files'])}. "
                "Select a higher tier or upload fewer documents."
            ),
        )

    started = time.perf_counter()
    timings = {
        "index_build_ms": 0.0,
        "retrieval_ms": 0.0,
        "generation_ms": 0.0,
    }
    try:
        stage_start = time.perf_counter()
        index = _build_index(session, request.model)
        timings["index_build_ms"] = round(
            (time.perf_counter() - stage_start) * 1000, 2
        )
        # Measure initial and corrective retrieval, including reranking.
        stage_start = time.perf_counter()
        hits = _retrieve(request.question, request.model, index)
        corrective_attempted = False
        # Advanced tier: one controlled corrective pass with alternative query views
        # when the first pass does not pass the evidence sufficiency heuristic.
        if request.model == "model_3" and not _evidence_sufficient(request.question, hits):
            corrective_attempted = True
            retry_hits = []
            seen = {h["chunk"].chunk_id for h in hits}
            for variant in _query_variants(request.question)[1:]:
                for candidate in _retrieve(variant, request.model, index):
                    cid = candidate["chunk"].chunk_id
                    if cid not in seen:
                        retry_hits.append(candidate)
                        seen.add(cid)
            combined = hits + retry_hits
            combined.sort(
                key=lambda hit: (
                    hit.get("rerank_score")
                    if hit.get("rerank_score") is not None
                    else hit.get("fusion_score", 0.0)
                ),
                reverse=True,
            )
            hits = combined[:TIERS[request.model]["final_k"]]
        timings["retrieval_ms"] = round(
            (time.perf_counter() - stage_start) * 1000, 2
        )
        if not _evidence_sufficient(request.question, hits):
            answer = (
                "I could not find sufficient evidence in the uploaded documents "
                "to answer this confidently. The documents may not contain the "
                "requested information."
            )
            used_hits, generation_warning, input_tokens = [], None, 0
            status = "insufficient_evidence"
        else:
            effective_budget = min(request.token_budget, int(cfg["context_cap"]))
            stage_start = time.perf_counter()
            answer, used_hits, generation_warning, input_tokens = _generate(
                request.question,
                hits,
                request.model,
                effective_budget,
            )
            timings["generation_ms"] = round(
                (time.perf_counter() - stage_start) * 1000, 2
            )
            status = "answered" if not generation_warning else "extractive_fallback"
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}") from exc

    sources = []
    for rank, hit in enumerate(used_hits, start=1):
        chunk = hit["chunk"]
        sources.append({
            "rank": rank,
            "text": hit.get("context_text", chunk.text),
            "filename": chunk.filename,
            "page": chunk.page,
            "chunk_id": chunk.chunk_id,
            "score": round(float(hit.get("dense_score", 0.0)), 4),
            "fusion_score": round(float(hit.get("fusion_score", 0.0)), 6),
            "rerank_score": (
                round(float(hit["rerank_score"]), 4)
                if hit.get("rerank_score") is not None
                else None
            ),
            "bm25_score": round(float(hit.get("bm25_score", 0.0)), 4),
            "retrieval_trace": hit.get("retrieval_trace", {}),
        })
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    effective_budget = min(request.token_budget, int(cfg["context_cap"]))
    return {
        "answer": answer,
        "status": status,
        "model": request.model,
        "model_name": cfg["name"],
        "target_accuracy": cfg["target_accuracy"],
        "accuracy_notice": "Target only; actual accuracy must be measured on a labelled benchmark.",
        "retrieval_strategy": cfg["retrieval"],
        "embedding_model": cfg["embedding_model"],
        "reranker_model": cfg["reranker_model"],
        "sources": sources,
        "retrieved_count": len(sources),
        "chunk_count": len(session["chunks"]),
        "document_count": len(session["files"]),
        "files": session["files"],
        "latency_ms": latency_ms,
        "timings": timings,
        "gpu": _get_gpu_metrics(),
        "generator_model": GENERATOR_MODEL,
        "requested_token_budget": request.token_budget,
        "effective_context_budget": effective_budget,
        "generation_input_tokens": input_tokens,
        "output_token_limit": cfg["output_tokens"],
        "generation_warning": generation_warning,
        "corrective_retrieval_attempted": corrective_attempted,
        "retrieval_trace": {
            "stages": [
                {
                    "name": "Dense retrieval",
                    "status": "complete",
                    "detail": index["embedding_model"],
                },
                {
                    "name": "BM25 keyword retrieval",
                    "status": (
                        "complete" if cfg["retrieval"] != "dense" else "skipped"
                    ),
                    "detail": (
                        "Keyword candidates"
                        if cfg["retrieval"] != "dense"
                        else "Lite tier uses dense retrieval only"
                    ),
                },
                {
                    "name": "RRF fusion",
                    "status": (
                        "complete" if cfg["retrieval"] != "dense" else "skipped"
                    ),
                    "detail": (
                        "Reciprocal-rank fusion"
                        if cfg["retrieval"] != "dense"
                        else "Not used in Lite"
                    ),
                },
                {
                    "name": "Cross-encoder reranking",
                    "status": "complete" if cfg["reranker_model"] else "skipped",
                    "detail": (
                        cfg["reranker_model"] or "Not configured for this tier"
                    ),
                },
                {
                    "name": "Corrective retrieval",
                    "status": (
                        "attempted" if corrective_attempted else "not_needed"
                    ),
                    "detail": (
                        "Alternative query views tried"
                        if corrective_attempted
                        else "No retry triggered"
                    ),
                },
                {
                    "name": "Evidence check",
                    "status": (
                        "passed" if status == "answered" else "failed_or_fallback"
                    ),
                    "detail": status,
                },
            ],
            "query_variants": (
                _query_variants(request.question)
                if request.model == "model_3"
                else [request.question]
            ),
        },
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
