# Execution & Data Flows

This document details the step-by-step execution pipelines, sequence diagrams, and decision trees powering the **Cost-Aware Knowledge Engine**.

---

## 1. Document Ingestion & Knowledge Indexing Flow

When a user uploads a document (PDF, TXT, or scan receipt) through the **Document Hub**, it undergoes a deterministic multi-stage parsing and indexing pipeline:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant API as FastAPI (/documents/upload)
    participant Parser as DocumentParser
    participant Struct as StructureDetector
    participant Chunker as ChunkingEngine
    participant FactExt as FactExtractor
    participant Embed as EmbeddingService
    participant DB as Relational DB (PostgreSQL / SQLite)

    User->>API: POST /documents/upload (Multipart file)
    API->>Parser: Extract page-by-page text (PyMuPDF / pdfplumber)
    Parser-->>API: List[PageData] (page_number, text)
    
    API->>API: Compute SHA-256 Checksum over extracted content
    API->>DB: Check if document checksum exists (Deduplication)
    alt Already Indexed
        DB-->>API: Existing Document record
        API-->>User: Return 200 (Already indexed, skipping redundant work)
    else New Document
        API->>DB: INSERT INTO documents & document_pages
        
        API->>Struct: Detect layout (sections, key-value candidates, tables)
        Struct-->>API: DocumentStructure (sections, tables, kv_pairs)
        
        par Parallel Chunking
            API->>Chunker: Sliding-Window Chunks (fixed tokens, overlap)
            API->>Chunker: Semantic Chunks (heading & boundary aware)
        end
        Chunker-->>API: List[DocumentChunk] with deterministic IDs
        API->>DB: INSERT INTO document_chunks

        API->>FactExt: Extract key-value facts & tables
        FactExt-->>API: List[KnowledgeFact], List[KnowledgeTable]
        API->>DB: INSERT INTO knowledge_facts & knowledge_tables

        API->>Embed: Generate vector embeddings for chunks
        Embed-->>API: List[EmbeddingVector]
        API->>DB: INSERT INTO embeddings
        
        API->>DB: COMMIT transaction
        API-->>User: Ingestion Complete (doc_id, chunks_count, facts_count)
    end
```

### Key Stages in Ingestion:
1. **Extraction & Sanitization:** Text is extracted per page. If the file is a PDF, [`PyMuPDF`](https://pymupdf.readthedocs.io/) extracts layout blocks and textual streams.
2. **Deterministic Checksumming:** A cryptographic SHA-256 hash is generated from normalized page text to provide idempotent deduplication.
3. **Dual Chunking Strategy:**
   - **Sliding-Window Chunks:** Configurable window size (e.g., 200 words, 40-word overlap) ensures continuity across sentence boundaries.
   - **Semantic Chunks:** Chunk boundaries respect document headers, paragraphs, and logical sections.
4. **Structured Knowledge Extraction:** Key-value pairs (e.g., `Receipt Number: LR-00501`, `Total: $450.00`, `Date: 2026-08-15`) are extracted with confidence scores and persisted into `knowledge_facts`.
5. **Deterministic Chunk Hashing:** Each chunk is assigned a stable unique key derived from:
   $$\text{chunk\_id} = \text{hash}(\text{doc\_checksum} + \text{strategy} + \text{page} + \text{index} + \text{text})$$

---

## 2. Query Resolution & Multi-Tier Routing Flow

Every query submitted to the `/queries/answer` endpoint traverses an intelligent multi-tiered decision tree designed to minimize latency and eliminate unnecessary LLM inference costs:

```mermaid
flowchart TD
    Start(["User submits query"]) --> Normalize["Normalize Query<br/>(Lowercase, strip punctuation, trim whitespace)"]
    Normalize --> CacheCheck{"Check In-Memory<br/>LRU Cache?"}

    %% Tier 0: Cache Hit
    CacheCheck -- "Cache Hit (Tier 0)" --> ReturnCache["Return Cached Response<br/>Latency: < 2ms | Cost: $0.000000"]
    ReturnCache --> End(["Finish"])

    %% Tier 1: Deterministic Fact Extraction
    CacheCheck -- "Cache Miss" --> AnalyzeRoute["Analyze Query Intent & Route<br/>(Lookup, Factoid, Search, Summary)"]
    AnalyzeRoute --> Retrieve["Execute Hybrid Retrieval<br/>1. Exact Fact Search (knowledge_facts)<br/>2. Lexical BM25 (document_chunks)<br/>3. Vector Cosine Similarity (embeddings)"]
    
    Retrieve --> Deterministic{"Exact Fact Match<br/>Confidence >= 0.8?"}
    Deterministic -- "Yes (Tier 1)" --> ExtractFact["Extract Structured Fact Answer<br/>Latency: < 15ms | Cost: $0.000000"]
    
    %% Tier 2: Hybrid Retrieval Selection
    Deterministic -- "No" --> ScoreRetrieved{"Top Chunk Retrieval<br/>Score >= 0.3?"}
    ScoreRetrieved -- "Yes & High Confidence" --> ExtractPassage["Synthesize Answer from Highest Scored Chunk<br/>Latency: < 40ms | Cost: $0.000001"]

    %% Tier 3: LLM Fallback
    ScoreRetrieved -- "No / Low Confidence" --> CheckLLM{"LLM Fallback Allowed<br/>& API Key Available?"}
    CheckLLM -- "Yes (Tier 3)" --> PromptLLM["Construct Constrained Prompt with Top Chunks<br/>Call OpenRouter LLM Provider<br/>Latency: ~600ms | Cost: ~$0.002000"]
    CheckLLM -- "No / Disabled" --> GracefulFail["Return Best Available Retrieval Context<br/>with Confidence Flag"]

    %% Final aggregation
    ExtractFact --> CostRecord["Record Telemetry in CostTracker<br/>(Retrieval cost, LLM tokens, latency, tier)"]
    ExtractPassage --> CostRecord
    PromptLLM --> CostRecord
    GracefulFail --> CostRecord

    CostRecord --> StoreCache["Save Response in Query Cache"]
    StoreCache --> ReturnResponse["Return QueryResponse to Client with Evidence & Usage"]
    ReturnResponse --> End
```

---

## 3. Tier Comparison Matrix

| Tier | Name | Trigger Condition | Average Latency | Estimated Cost | Accuracy Profile |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | **Normalized Cache** | Identical normalized query previously answered | `< 2 ms` | **$0.000000** | $100\%$ deterministic |
| **Tier 1** | **Structured Fact Extractor** | Exact field match in `knowledge_facts` with confidence $\ge 0.8$ | `< 15 ms` | **$0.000000** | Exact grounded extraction |
| **Tier 2** | **Hybrid Lexical & Semantic** | BM25 match or vector cosine similarity chunk score $\ge 0.3$ | `< 40 ms` | **$0.000001** | High recall, zero hallucinations |
| **Tier 3** | **Constrained LLM Fallback** | Extraction confidence $< 0.3$ and `llm_allowed = true` | `~600 ms` | **~$0.002000** | Generative synthesis from top chunks |

---

## 4. Cascaded Document Deletion Flow

Deleting a document in the **Document Hub** triggers an atomic transaction across all relational tiers to ensure clean garbage collection without orphaned vectors:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Admin
    participant API as FastAPI (DELETE /documents/{id})
    participant DB as Relational Database

    User->>API: Click Delete on Document Card
    API->>DB: SELECT * FROM documents WHERE id = :id
    alt Document not found
        DB-->>API: None
        API-->>User: 404 Not Found
    else Document found
        API->>DB: BEGIN Transaction
        API->>DB: DELETE FROM embeddings WHERE document_id = :id
        API->>DB: DELETE FROM knowledge_facts WHERE document_id = :id
        API->>DB: DELETE FROM knowledge_tables WHERE document_id = :id
        API->>DB: DELETE FROM document_chunks WHERE document_id = :id
        API->>DB: DELETE FROM document_pages WHERE document_id = :id
        API->>DB: DELETE FROM documents WHERE id = :id
        API->>DB: COMMIT Transaction
        API-->>User: 200 OK (Document & all cascaded entities removed)
    end
```

---

## 5. Cost Tracking & Observability Data Flow

The cost telemetry engine records every query event in real time:

1. **Query Event Ingestion:** Captures query text, resolution tier, prompt tokens, completion tokens, LLM API expenditure, and retrieval baseline cost.
2. **Cumulative Aggregation:** In-memory counters calculate running totals for queries, tokens, and micro-dollar expenditures.
3. **Counterfactual Savings Estimation:** Evaluates total cost against an enterprise baseline where every query is routed to a full LLM call:
   $$\text{Savings} = (\text{Total Queries} \times \$0.002000) - \text{Actual Engine Spend}$$
4. **Client Polling & Live Sync:** The frontend **Cost Dashboard** queries `GET /metrics/costs` to render live spending curves, savings gauges, and query distribution charts.
