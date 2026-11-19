# Scholar AI — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Client                            │
│  HTML5 + CSS3 + Vanilla JS + PDF.js + Marked.js             │
│                                                             │
│  Pages: Home | Chat | Library | Compare | Summarize |       │
│         Insights | Settings                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (HTTP JSON)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                 Flask Backend (Python 3.11)                  │
│                                                             │
│  Routes (Blueprints)                                        │
│  ├── /health          → Health checks                       │
│  ├── /documents       → Upload, list, delete, serve PDF     │
│  ├── /chat            → RAG Q&A, conversations              │
│  ├── /research        → Summaries, compare, insights, search│
│  ├── /notes           → CRUD notes                          │
│  ├── /collections     → CRUD collections                    │
│  └── /exports         → Markdown downloads                  │
│                                                             │
│  Services                                                   │
│  ├── pdf_service.py       PyMuPDF text extraction           │
│  ├── chunking_service.py  Sentence-aware overlapping chunks │
│  ├── embedding_service.py Sentence Transformers (local)     │
│  ├── vector_store.py      FAISS index management            │
│  ├── gemini_service.py    Google Gemini API calls           │
│  └── rag_service.py       Pipeline orchestration            │
└──────────┬────────────────────────┬────────────────────────-┘
           │                        │
           ▼                        ▼
┌──────────────────┐    ┌─────────────────────────┐
│   SQLite (ORM)   │    │  FAISS Indexes (disk)    │
│                  │    │                          │
│  Documents       │    │  {doc_id}.index          │
│  DocumentChunks  │    │  {doc_id}.meta.json      │
│  Conversations   │    │                          │
│  Messages        │    │  Inner Product search    │
│  Summaries       │    │  (cosine similarity on   │
│  Notes           │    │   normalized embeddings) │
│  Collections     │    └──────────────────────────┘
│  Insights        │
│  ProcessingJobs  │         ┌─────────────────────┐
└──────────────────┘         │  Google Gemini API   │
                             │  (external, HTTPS)   │
                             │                      │
                             │  gemini-1.5-flash    │
                             └─────────────────────-┘
```

## RAG Pipeline

```
User Question
     │
     ▼
[1] Embed Query
    └─ Sentence Transformers all-MiniLM-L6-v2
     │
     ▼
[2] FAISS Search
    └─ Top-K=5 nearest neighbor search per document
     │
     ▼
[3] Chunk Enrichment
    └─ Retrieve full text + page numbers from SQLite
     │
     ▼
[4] Context Building
    └─ Format retrieved chunks with [Source N | Page P] labels
     │
     ▼
[5] Gemini Prompt
    └─ System + context + conversation history + question
     │
     ▼
[6] Citation Extraction
    └─ Parse source references, validate against DB
     │
     ▼
[7] Response
    └─ Answer + citations + follow-up questions → frontend
```

## Data Flow: Document Upload

```
PDF File → Validate → Hash (dedup check) → Store to disk
     │
     └─ Background thread:
          Extract pages (PyMuPDF)
          │
          Chunk text (sentence-aware, overlapping)
          │
          Generate embeddings (SentenceTransformers)
          │
          Store chunks in SQLite
          │
          Build FAISS index → save to disk
          │
          Update document status → "ready"
```

## Database Schema

```
documents          ←── document_chunks
    │id                     │id
    │title                  │document_id (FK)
    │file_path              │chunk_index
    │status                 │content
    │total_pages            │page_number
    │chunk_count            │faiss_index_id
    │embedding_model
    │
    ├──→ summaries
    │       │summary_type
    │       │content
    │       │structured_data (JSON)
    │
    ├──→ notes
    │       │page_number
    │       │content
    │
    ├──→ insights
    │       │insight_type
    │       │structured_data (JSON)
    │
    └──→ collection_documents ←── collections
                                      │id
                                      │name

conversations ──→ messages
    │id                │id
    │title             │role (user|assistant)
    │document_ids JSON │content
                       │citations JSON
                       │follow_up_questions JSON
```

