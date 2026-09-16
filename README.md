# Cost-Aware Knowledge Engine

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An **enterprise retrieval-first document intelligence platform** engineered to minimize LLM inference costs. By combining **deterministic key-value extraction**, **dual-strategy chunking**, **hybrid BM25/vector search**, and an **in-memory LRU query cache**, the engine resolves high-frequency document questions with **zero LLM cost** and sub-15ms latency, reserving generative LLM calls strictly as a fallback.

---

## 📚 Documentation Quick Links

| Document | Description |
| :--- | :--- |
| 📐 [**System Architecture (`architecture.md`)**](architecture.md) | In-depth technical architecture, FastAPI gateway, 4-tier engine, SQLAlchemy models, pgvector, and data schema. |
| 🔄 [**Execution & Data Flows (`flow.md`)**](flow.md) | Mermaid sequence diagrams and decision trees for document ingestion, query routing, tier comparisons, and cascaded deletion. |

---

## 🚀 Key Features

- **Cost-Optimized Multi-Tier Answering:**
  - **Tier 0 (Cache):** Normalized query memory cache (< 2ms, $0.00 spend).
  - **Tier 1 (Deterministic Extraction):** Structured entity and fact extraction (< 15ms, $0.00 spend).
  - **Tier 2 (Hybrid Retrieval):** Lexical BM25 + vector similarity ranking (< 40ms, amortized $0.000001 spend).
  - **Tier 3 (LLM Fallback):** OpenRouter generative model invoked only when retrieval confidence is below threshold (< 0.3).
- **Dual Chunking & Extraction Engine:**
  - **Sliding-Window Chunking:** Fixed-token windows with configurable overlap to preserve contextual continuity.
  - **Semantic Chunking:** Boundary-aware chunking respecting headings, paragraphs, and logical sections.
  - **Fact Extraction:** Automated key-value pair and structured table recognition.
- **Enterprise Web Interface (React 19 + Vite):**
  - **Document Hub:** Multi-file drag-and-drop uploader, page/chunk inspection modal, and atomic cascaded deletion.
  - **Query Studio:** Interactive Q&A interface with query suggestions, confidence meters, routing tier indicators, and verifiable quote citations.
  - **Cost Telemetry Dashboard:** Real-time spend tracking, token usage economics, query duration latency, and counterfactual LLM savings analytics.
  - **Search Lab:** Deep search inspector to analyze raw BM25 lexical scores, vector cosine similarities, and chunk strategies.
- **Dual Database Flexibility:** Runs out-of-the-box on local **SQLite** (zero external dependencies) or scales to **PostgreSQL with pgvector**.

---

## ⚡ Quick Start

### 1. Backend Setup

From the repository root:

```powershell
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Initialize the database schema
python scripts\init_db.py

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

---

### 2. Frontend Setup

In a separate terminal:

```powershell
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite dev server
npm run dev
```

Open your browser at `http://localhost:5173` to access the web application.

---

## ⚙️ Configuration & Environment Variables

Copy the example environment configuration:

```powershell
Copy-Item backend\.env.example backend\.env
```

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./cost_aware_knowledge_engine.db` | Database connection string (SQLite or PostgreSQL). |
| `ENABLE_PGVECTOR` | `false` | Enable native pgvector storage in PostgreSQL. |
| `EMBEDDING_PROVIDER` | `deterministic` | Provider (`deterministic` for fast local dev, or real vector models). |
| `EMBEDDING_MODEL` | `deterministic-hash-v1` | Embedding model identifier. |
| `EMBEDDING_DIMENSIONS` | `384` | Dimensionality of embedding vectors. |
| `OPENROUTER_API_KEY` | `""` | Optional OpenRouter API key for Tier 3 LLM fallback. |
| `OPENROUTER_MODEL` | `google/gemini-2.5-flash` | Fallback LLM model on OpenRouter. |
| `RETRIEVAL_COST_PER_QUERY` | `0.000001` | Base amortized query compute cost. |

---

## 📡 API Reference Overview

### Documents API (`/documents`)

- `POST /documents/upload`: Upload and ingest PDF/TXT documents.
- `GET /documents`: List all indexed documents with page, chunk, fact, and table counts.
- `GET /documents/{id}`: Detailed inspection of extracted pages, chunks, and key-value facts.
- `DELETE /documents/{id}`: Cascaded deletion across all child entities.

### Queries API (`/queries`)

- `POST /queries/answer`: Execute multi-tier query resolution pipeline with cost tracking and evidence citations.
- `GET /queries/search`: Raw hybrid retrieval across lexical chunks, vector embeddings, and facts.

### Metrics API (`/metrics`)

- `GET /metrics/costs`: Telemetry statistics, query logs, and estimated cost savings.
- `POST /metrics/costs/reset`: Reset runtime cost tracker records.
- `GET /metrics/overview`: System-wide counts of documents, chunks, facts, embeddings, and active cache items.

---

## 🧪 Running Tests

From the `backend` directory:

```powershell
# Run full test suite
pytest

# Run manual smoke tests
python test_chunker.py
python test_semantic_chunker.py
python test_structure_detector.py
```

---

## 📁 Repository Structure

```
cost-aware-knowledge-engine/
├── README.md                  # Main overview & quick start
├── architecture.md            # In-depth technical architecture
├── flow.md                    # Data flows, sequence diagrams & decision trees
├── documents/
│   └── raw/                   # Sample test documents & receipts
├── backend/
│   ├── app/
│   │   ├── api/routes/        # FastAPI route handlers (documents, queries, metrics)
│   │   ├── core/              # Global configuration & settings
│   │   ├── db/                # Database engine & session management
│   │   ├── models/            # SQLAlchemy models (Document, Chunk, Fact, Embedding)
│   │   └── services/
│   │       ├── answering/     # Deterministic AnswerExtractor
│   │       ├── cache/         # In-memory LRU query cache
│   │       ├── chunking/      # Sliding-window & semantic chunkers
│   │       ├── cost_tracker.py# Real-time cost & token accounting
│   │       ├── embeddings/    # Pluggable vector embedding providers
│   │       ├── ingestion/     # Document parsing (PDF & TXT)
│   │       ├── knowledge/     # KnowledgeIndexer service
│   │       ├── llm/           # OpenRouter LLM provider wrapper
│   │       ├── retrieval/     # Hybrid search orchestrator
│   │       └── routing/       # Query analyzer & normalizer
│   ├── scripts/               # DB init & utility scripts
│   └── requirements.txt       # Python backend dependencies
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── Navbar.jsx         # Header & health status pill
    │   │   ├── DocumentHub.jsx    # Document management & chunk inspection
    │   │   ├── QueryStudio.jsx    # Cost-aware Q&A with evidence
    │   │   ├── CostDashboard.jsx  # Telemetry & savings dashboard
    │   │   └── SearchLab.jsx      # Hybrid retrieval inspector
    │   ├── App.jsx            # Main app container & routing
    │   ├── App.css            # Dark mode tokens & glassmorphic styles
    │   └── index.css          # Base typography & layout primitives
    ├── package.json           # Frontend dependencies (React 19, Lucide)
    └── vite.config.js         # Vite configuration
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
