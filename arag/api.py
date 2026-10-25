from pathlib import Path
import shutil

from fastapi import File, FastAPI, UploadFile

from arag.config import load_config
from arag.ingestion.pipeline import ingest_directory

app = FastAPI(title="ARAG API", version="0.1.0")
config = load_config()


@app.get("/health")
def health():
    return {"status": "ok", "project": "ARAG"}


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    raw = Path(config["paths"]["raw"])
    raw.mkdir(parents=True, exist_ok=True)
    destination = raw / file.filename

    with destination.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    chunks = ingest_directory(
        raw,
        config["paths"]["processed"] + "/chunks.jsonl",
        config["ingestion"]["chunk_size"],
        config["ingestion"]["chunk_overlap"],
    )
    return {"filename": file.filename, "chunks": len(chunks)}
