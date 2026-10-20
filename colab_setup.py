# Run this from a Colab cell:
# !git clone YOUR_REPOSITORY_URL
# %cd ARAG
# !pip install -r requirements-colab.txt

from pathlib import Path
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)
Path("data/index").mkdir(parents=True, exist_ok=True)

print("ARAG Colab workspace ready.")
