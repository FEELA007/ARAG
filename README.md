# ARAG v2 — Adaptive, Reliable & Cost-Aware Retrieval-Augmented Generation

An evidence-grounded question-answering system that allows users to upload documents and ask questions about their content. ARAG v2 retrieves relevant passages, generates answers using a language model, and displays supporting evidence and retrieval pipeline information.

## Overview

ARAG v2 is a Retrieval-Augmented Generation (RAG) application designed to make document question-answering more transparent and configurable.

Instead of relying only on a language model's existing knowledge, the system retrieves relevant passages from uploaded documents and uses that evidence to answer user questions.

The application provides multiple retrieval configurations so users can explore the trade-offs between retrieval complexity, relevance, and response time.

## Features

- **Document upload:** Upload PDF, DOCX, and TXT files.
- **Document indexing:** Split document content into chunks and prepare it for retrieval.
- **Multiple retrieval tiers:** Compare Lite, Standard, and Advanced retrieval configurations.
- **Dense retrieval:** Retrieve semantically relevant passages using sentence embeddings.
- **Hybrid retrieval:** Combine semantic retrieval with BM25 keyword search.
- **Reciprocal Rank Fusion (RRF):** Combine ranked results from multiple retrieval methods.
- **Cross-encoder reranking:** Reorder candidate passages according to their relevance to a question when configured.
- **Corrective retrieval:** Attempt additional retrieval when the Advanced tier's evidence checks indicate that the initial results may be insufficient.
- **Evidence-grounded answers:** Display retrieved source passages alongside generated answers.
- **Pipeline trace:** Inspect which retrieval stages ran, were skipped, or were unnecessary.
- **Performance metrics:** Display query latency and other available backend performance measurements.
- **GPU support:** Use CUDA-compatible PyTorch for supported model workloads when available.

> Retrieval scores indicate relevance signals; they do not independently establish answer accuracy. Actual accuracy must be evaluated using a labelled test dataset.

## Architecture

```text
                    ┌──────────────────────┐
                    │      Web Frontend    │
                    │    HTML / CSS / JS   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │     FastAPI Backend  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Document Processing  │
                    │ Chunking & Indexing  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Retrieval Engine   │
                    │                      │
                    │ Dense / Hybrid Search│
                    │ RRF / Reranking      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Evidence Evaluation  │
                    │ & Corrective Search │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Answer Generation   │
                    │  & Source Display    │
                    └──────────────────────┘
```

## Retrieval Tiers

ARAG v2 provides three configurations.

| Tier | Retrieval approach | Purpose |
|---|---|---|
| Model 1 — Lite | Dense semantic retrieval | Provides a simpler retrieval pipeline |
| Model 2 — Standard | Dense retrieval, BM25, and RRF fusion | Combines semantic and keyword-based retrieval |
| Model 3 — Advanced | Hybrid retrieval, multi-query retrieval, cross-encoder reranking, and corrective retrieval when triggered | Adds retrieval and evidence-refinement stages |

The exact stages executed depend on the selected tier and the evidence checks performed for the query.

### Model 1 — Lite

Uses sentence embeddings to retrieve semantically relevant document chunks.

### Model 2 — Standard

Combines dense retrieval and BM25 keyword retrieval. Reciprocal Rank Fusion merges their ranked results.

### Model 3 — Advanced

Uses additional retrieval techniques, including query variations and cross-encoder reranking. Corrective retrieval may run when the initial evidence is considered insufficient.

## Technology Stack

| Component | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Semantic retrieval | Sentence Transformers |
| Keyword retrieval | BM25 |
| Rank fusion | Reciprocal Rank Fusion |
| Reranking | Cross-encoder model |
| Language model | Configurable Hugging Face text-generation model |
| Machine learning | PyTorch |
| GPU acceleration | CUDA, when available |

## Project Structure

The main project files are organized as follows:

```text
ARAG_v2/
├── backend/
│   └── app.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── arag/
│   ├── evaluation/
│   └── retrieval/
├── README.md
└── requirements.txt
```

The complete project may contain additional modules and configuration files.

## Requirements

- Python 3.10 or another Python version supported by the project's dependencies.
- pip
- A modern web browser
- Internet access for downloading model files when they are not already cached.
- Optional: an NVIDIA GPU and a compatible CUDA-enabled PyTorch installation.

The required Python packages should be installed from the project's dependency file.

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ARAG_v2
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository's actual clone URL.

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python executable directly or follow your system's virtual-environment activation guidance.

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If your `requirements.txt` does not specify the appropriate PyTorch build, install the PyTorch version compatible with your hardware and software environment. Consult the official PyTorch installation instructions before selecting a CUDA build.

### 4. Configure environment variables

Review the configuration in `backend/app.py` and any `.env.example` file provided by the project.

For example, the generator model may be configurable through:

```text
ARAG_GENERATOR_MODEL
```

If no override is provided, the current application configuration uses:

```text
Qwen/Qwen2.5-1.5B-Instruct
```

Use the actual configuration in your checkout as the source of truth.

## Running the Application

From the project root, activate the virtual environment and run:

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

If the backend starts successfully, open the frontend using the project's configured frontend-serving method.

The FastAPI interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The API documentation can be used to inspect available endpoints and test requests.

> If the frontend is served separately, configure it to communicate with the correct backend address. Follow the serving method and API configuration implemented in your checkout.

## How to Use

1. Start the backend.
2. Open the ARAG v2 frontend.
3. Upload a PDF, DOCX, or TXT document.
4. Select a retrieval tier.
5. Enter a question about the uploaded document.
6. Review the generated answer.
7. Inspect the retrieved passages and source evidence.
8. Review the Pipeline Trace to understand which retrieval stages executed.
9. Examine the reported latency and other available performance metrics.

### Example

Suppose an uploaded employee handbook contains the following statement:

> Full-time employees receive 12 days of annual leave per calendar year.

**Question:**

How many annual leave days do employees receive per year?

**Expected answer:**

Full-time employees receive 12 days of annual leave per calendar year.

The retrieved source passage should support the answer.

This example illustrates the intended behavior; it is not a claim about measured benchmark performance.

## Evaluation and Testing

ARAG v2 can be evaluated by asking questions whose answers are explicitly stated in uploaded documents.

A useful test set should include:

- Direct factual questions.
- Questions requiring multiple pieces of evidence.
- Questions involving specific dates, quantities, and conditions.
- Questions that require combining information from different sections.
- Questions for which the document provides no answer.

Compare the three retrieval tiers using the same questions and documents.

Suggested evaluation criteria:

| Metric | Purpose |
|---|---|
| Answer correctness | Checks whether the generated answer matches the reference answer |
| Evidence relevance | Checks whether retrieved passages support the answer |
| Retrieval latency | Measures the time spent retrieving relevant passages |
| End-to-end latency | Measures the overall query-response time |
| Evidence sufficiency | Checks whether enough supporting information was retrieved |
| Unsupported-answer handling | Checks whether the system avoids inventing information absent from the document |

Retrieval scores, response time, and model configuration should not be treated as substitutes for a labelled accuracy evaluation.

## GPU Support

ARAG v2 can use CUDA-compatible PyTorch for supported workloads when a compatible NVIDIA GPU and software environment are available.

To check the PyTorch and CUDA installation, run:

```powershell
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not detected')"
```

The reported GPU name and CUDA availability reflect the active Python environment. GPU memory measurements and overall GPU utilization are different metrics.

## Troubleshooting

### Backend does not start

Check that the virtual environment is activated and that the project's dependencies are installed.

### Models take a long time to load

The first run may need to download model files and initialize model components. Later requests may be faster when those components remain cached.

### No answer is found

Check whether the uploaded document contains the information requested. Review the retrieved passages and the Pipeline Trace.

### Performance metrics are missing

Confirm that the backend returns the expected fields and that the frontend uses matching element IDs and response-property names.

### CUDA is unavailable

Verify that the active virtual environment has a compatible PyTorch installation and that the NVIDIA driver is working correctly.

## Limitations

- Answers depend on the quality and content of the uploaded documents.
- Retrieval can miss relevant passages.
- Generated answers may still contain errors.
- A relevant source passage does not automatically guarantee a correct answer.
- Performance depends on the selected models, document size, hardware, and caching.
- Actual accuracy and reliability require systematic evaluation.

## Future Improvements

Potential areas for further development include:

- Benchmark-based comparison of retrieval tiers.
- More comprehensive answer-quality evaluation.
- Improved retrieval diagnostics.
- Better latency and resource-usage reporting.
- Expanded document-format support.
- More extensive automated testing.

## Contributing

Contributions, bug reports, and suggestions are welcome.

Before submitting changes, test the affected functionality and describe the changes made.

## License

No license has been specified here. Add an appropriate `LICENSE` file before distributing the project publicly, and ensure that the chosen license is compatible with the project's dependencies and model licenses.

## Acknowledgements

ARAG v2 builds on the Python machine-learning ecosystem, including FastAPI, PyTorch, and Sentence Transformers, along with the retrieval and language models configured in the project.
