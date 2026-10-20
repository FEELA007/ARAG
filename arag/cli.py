import argparse
from arag.config import load_config
from arag.ingestion.pipeline import ingest_directory

def main():
    parser = argparse.ArgumentParser(description="ARAG CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest")
    ingest.add_argument("directory")

    args = parser.parse_args()
    cfg = load_config()

    if args.command == "ingest":
        chunks = ingest_directory(
            args.directory,
            cfg["paths"]["processed"] + "/chunks.jsonl",
            cfg["ingestion"]["chunk_size"],
            cfg["ingestion"]["chunk_overlap"],
        )
        print(f"Ingested {len(chunks)} chunks.")

if __name__ == "__main__":
    main()
