# Cost-Aware Knowledge Engine

Generic document intelligence backend for extracting text, chunking documents,
persisting knowledge, and indexing chunks for later retrieval.

## Backend Setup

Create or activate the backend virtual environment, then install dependencies:

```powershell
cd backend
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Environment Variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Important variables:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/cost_aware_knowledge_engine
EMBEDDING_PROVIDER=deterministic
EMBEDDING_MODEL=deterministic-hash-v1
EMBEDDING_DIMENSIONS=384
ENABLE_PGVECTOR=false
```

`deterministic` embeddings are local and dependency-free. They are useful for
tests and development, but production retrieval should use a real provider
behind the `EmbeddingProvider` abstraction.

## PostgreSQL Setup

Create the database:

```powershell
createdb cost_aware_knowledge_engine
```

Or from `psql`:

```sql
CREATE DATABASE cost_aware_knowledge_engine;
```

## pgvector Setup

The current implementation stores embeddings through a provider-agnostic JSON
column so it works in local SQLite tests and standard PostgreSQL. To enable
pgvector in PostgreSQL, install the extension for your PostgreSQL distribution,
then set:

```env
ENABLE_PGVECTOR=true
```

Initialize the extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The database initialization script also runs this statement when
`ENABLE_PGVECTOR=true`. A future migration can change the `embeddings.embedding`
storage column from JSON to a native `vector(n)` column without changing the
indexing service API.

## Database Initialization

From the `backend` directory:

```powershell
.\venv\Scripts\python.exe scripts\init_db.py
```

This creates:

- `documents`
- `document_pages`
- `document_chunks`
- `knowledge_facts`
- `knowledge_tables`
- `embeddings`

## Indexing Flow

The indexing service is `app.services.knowledge.knowledge_indexer.KnowledgeIndexer`.
It persists:

document -> pages -> sliding-window chunks -> semantic chunks -> facts -> embeddings

It is idempotent. Documents use a checksum of extracted page text, chunks use
stable IDs derived from document checksum, strategy, page, index, and text, and
embeddings are unique per chunk/provider/model.

Minimal Python usage from `backend`:

```python
from app.db import SessionLocal, init_db
from app.services.ingestion.document_parser import extract_text
from app.services.knowledge.knowledge_indexer import KnowledgeIndexer

init_db()

db = SessionLocal()
pages = extract_text("../documents/raw/LR-00501-receipt.pdf")
stats = KnowledgeIndexer(db).index_document(
    filename="LR-00501-receipt.pdf",
    file_type=".pdf",
    pages=pages,
)
db.commit()
db.close()

print(stats)
```

## Test Commands

From the `backend` directory:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Manual extraction smoke tests:

```powershell
.\venv\Scripts\python.exe test_chunker.py
.\venv\Scripts\python.exe test_semantic_chunker.py
.\venv\Scripts\python.exe test_structure_detector.py
```

## Run API

From the `backend` directory:

```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```
