import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arag.generation.generator import ExtractiveGenerator
from arag.ingestion.pipeline import ingest_document
from arag.retrieval.dense import DenseRetriever

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED_TYPES = ["pdf", "docx", "txt"]
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

st.set_page_config(page_title="ARAG Lite", page_icon="A", layout="wide")
st.title("ARAG Lite")
st.caption("A lightweight, single-document Retrieval-Augmented Generation prototype")
st.info(
    "Upload one document (PDF, DOCX, or TXT), up to 10 MB. "
    "This baseline uses MiniLM dense retrieval and evidence excerpts."
)

with st.sidebar:
    st.header("Configuration")
    st.write("Embedding model: `all-MiniLM-L6-v2`")
    st.write("Retrieval: Dense semantic search")
    st.write("Documents per session: 1")
    st.write("Maximum file size: 10 MB")
    st.caption("The 75% figure is a target to test, not a guaranteed accuracy result.")

uploaded = st.file_uploader(
    "Choose one document",
    type=SUPPORTED_TYPES,
    accept_multiple_files=False,
    help="Only one file can be processed at a time. Maximum size: 10 MB.",
)

if uploaded is not None:
    if uploaded.size > MAX_FILE_BYTES:
        st.error("This file exceeds the 10 MB limit. Please choose a smaller file.")
        st.stop()

    if st.button("Process document", type="primary"):
        with st.spinner(
            "Extracting text and building the retrieval index. "
            "The first run may download MiniLM."
        ):
            raw_dir = ROOT / "data" / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            # Keep only the currently selected document to prevent mixing old files.
            for old_file in raw_dir.iterdir():
                if old_file.is_file():
                    old_file.unlink()
            safe_name = Path(uploaded.name).name
            file_path = raw_dir / safe_name
            file_path.write_bytes(uploaded.getvalue())

            chunks = ingest_document(file_path, chunk_size=700, overlap=100)
            if not chunks:
                st.session_state.pop("arag_chunks", None)
                st.session_state.pop("arag_retriever", None)
                st.error("No readable text was found. If this is a scanned PDF, OCR is required.")
                st.stop()

            retriever = DenseRetriever(EMBEDDING_MODEL)
            retriever.build(chunks)
            st.session_state["arag_chunks"] = chunks
            st.session_state["arag_retriever"] = retriever
            st.session_state["arag_filename"] = safe_name
            st.session_state["arag_chunk_count"] = len(chunks)
        st.success(f"Processed {uploaded.name}: {len(chunks)} text chunks created.")

chunks = st.session_state.get("arag_chunks")
retriever = st.session_state.get("arag_retriever")

if chunks and retriever:
    st.divider()
    left, right = st.columns(2)
    left.metric("Loaded document", st.session_state.get("arag_filename", "1 file"))
    right.metric("Text chunks", st.session_state.get("arag_chunk_count", len(chunks)))

    question = st.text_input(
        "Ask a question about the document",
        placeholder="For example: What are the main findings?",
    )
    if st.button("Get answer") and question.strip():
        with st.spinner("Finding relevant passages..."):
            hits = retriever.search(question.strip(), top_k=min(3, len(chunks)))
            evidence_chunks = [chunks[idx] for idx, _score in hits]
            answer = ExtractiveGenerator().generate(question.strip(), evidence_chunks)

        st.subheader("Answer from retrieved evidence")
        st.write(answer)
        st.subheader("Sources")
        for i, (idx, score) in enumerate(hits, start=1):
            chunk = chunks[idx]
            page = getattr(chunk, "page", None)
            filename = getattr(
                chunk,
                "filename",
                st.session_state.get("arag_filename", "Document"),
            )
            page_label = page if page else "not available"
            st.markdown(
                f"**{i}. {filename}** — page {page_label} · "
                f"similarity `{score:.3f}`"
            )
            st.write(chunk.text[:1200] + ("…" if len(chunk.text) > 1200 else ""))
            st.divider()
        st.caption(
            "Similarity is not an accuracy percentage. "
            "Verify answers against the source document."
        )

st.markdown("---")
st.caption(
    "ARAG Lite is a baseline prototype. Measure accuracy on a labelled set "
    "of questions before reporting a percentage."
)
