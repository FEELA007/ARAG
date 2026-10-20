# ARAG Lite — Low Version

A small baseline based on the supplied ARAG project. It processes **one document at a time** (PDF, DOCX, or TXT), with a **10 MB maximum file size**.

## What it includes
- Text extraction from PDF, DOCX, and TXT files
- Chunking with page metadata where available
- MiniLM sentence embeddings
- Dense semantic retrieval (top 3 passages)
- Evidence excerpt answer and source/page display
- Streamlit interface

## Run locally (Windows / VS Code)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-low.txt
streamlit run arag/gui/app.py
```

Open the local Streamlit URL shown in the terminal.

## Run in Google Colab

1. Upload/extract the project ZIP into the Colab runtime.
2. In a notebook cell, change directory to the extracted `ARAG` folder.
3. Run:

```python
%pip install -r requirements-low.txt
!streamlit run arag/gui/app.py --server.port 8501
```

Colab may require a tunnel to access the Streamlit web interface. Running locally in VS Code is simpler for this version.

## Accuracy note
The project does **not** claim a measured 75% accuracy by default. Accuracy depends on the documents, questions, and evaluation rubric. To test a 75% target, prepare a labelled set of at least 20–50 questions with reference answers, run each question through ARAG Lite, and calculate the fraction judged correct. Report the measured score and test-set size; do not present the target as a result before testing.

## Limitations
- Only one document is processed at a time; a newly processed document replaces the prior session's indexed document.
- Maximum upload size is 10 MB.
- Scanned PDFs need OCR, which is not included.
- The baseline returns the most relevant passage rather than using a separate generative LLM. It can miss answers when retrieval fails.
- Similarity scores are not accuracy percentages.
