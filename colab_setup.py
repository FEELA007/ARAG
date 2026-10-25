# Run this script from a Colab cell to create the project data directories.

from pathlib import Path
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/index").mkdir(parents=True, exist_ok=True)

print("ARAG Colab workspace ready.")
