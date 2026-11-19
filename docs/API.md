# Scholar AI — API Reference

## Base URL
`http://127.0.0.1:5000/api/v1`

## Common Response Format

### Success
```json
{ "field": "value" }
```

### Error
```json
{ "error": "Human-readable error message" }
```

---

## Health

### GET /health
Basic liveness check.

**Response 200:**
```json
{ "status": "ok", "service": "Scholar AI" }
```

### GET /health/ready
Dependency readiness check.

**Response 200/503:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "gemini_configured": true,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "upload_storage": "ok"
  }
}
```

---

## Documents

### POST /documents
Upload a PDF document.

**Content-Type:** `multipart/form-data`

**Form fields:**
- `file` (required): PDF file
- `title` (optional): Custom title

**Response 201:**
```json
{
  "message": "Document uploaded successfully, processing started",
  "document": {
    "id": "uuid",
    "title": "Paper Title",
    "status": "uploaded",
    "total_pages": 12,
    "created_at": "2024-01-01T00:00:00"
  }
}
```

**Errors:** 400 (invalid file), 409 (duplicate), 413 (too large)

---

### GET /documents
List all documents.

**Query params:** `status`, `search`, `sort_by`, `order`

**Response 200:**
```json
{ "documents": [...], "total": 5 }
```

---

### GET /documents/:id/status
Polling endpoint for processing status.

**Response 200:**
```json
{
  "document_id": "uuid",
  "status": "ready",
  "chunk_count": 42,
  "error_message": null,
  "job": { "status": "done", "progress": 100 }
}
```

---

## Chat

### POST /chat
Main RAG question-answering endpoint.

**Request:**
```json
{
  "question": "What methodology was used?",
  "document_ids": ["uuid1"],
  "conversation_id": "optional-uuid"
}
```

**Response 200:**
```json
{
  "conversation_id": "uuid",
  "message": {
    "id": "uuid",
    "role": "assistant",
    "content": "The paper uses...",
    "citations": [
      {
        "chunk_id": "uuid",
        "document_id": "uuid",
        "document_title": "Paper Title",
        "page_number": 4,
        "excerpt": "...relevant text...",
        "score": 0.87
      }
    ],
    "follow_up_questions": ["What are the results?", "..."]
  }
}
```

**Errors:** 400 (missing question/docs), 401 (bad API key), 429 (quota), 503 (Gemini unavailable)

---

## Research

### POST /documents/:id/summaries
Generate a structured summary.

**Request:**
```json
{ "summary_type": "detailed", "regenerate": false }
```
`summary_type`: `"short"` | `"detailed"` | `"section_wise"`

**Response 201:**
```json
{
  "summary": {
    "id": "uuid",
    "summary_type": "detailed",
    "content": "Markdown text...",
    "structured_data": {
      "executive_summary": "...",
      "methodology": "...",
      "main_findings": "..."
    }
  }
}
```

---

### POST /compare
Compare multiple papers.

**Request:**
```json
{ "document_ids": ["uuid1", "uuid2"] }
```

**Response 200:**
```json
{
  "documents": [{"id": "...", "title": "..."}],
  "comparison": {
    "overview": "...",
    "research_objectives": {"similarities": "...", "differences": "..."},
    "methodologies": {"similarities": "...", "differences": "..."},
    "common_themes": ["theme1"],
    "research_gaps": ["gap1"],
    "recommendation": "..."
  }
}
```

---

### GET /search
Search document chunks.

**Query params:** `q` (required), `type` (`semantic`|`keyword`), `document_id`, `limit`

**Response 200:**
```json
{
  "results": [
    { "chunk_id": "uuid", "document_id": "uuid", "content": "...", "page_number": 3, "score": 0.91 }
  ],
  "total": 5,
  "query": "your search query"
}
```

---

## Notes

### POST /notes
Create a note.

**Request:**
```json
{
  "content": "Important observation",
  "title": "Optional title",
  "document_id": "optional-uuid",
  "page_number": 5,
  "tags": ["methodology"]
}
```

---

## Export

### POST /exports
Export data as Markdown download.

**Request:**
```json
{
  "type": "summary",
  "resource_id": "summary-uuid"
}
```
`type`: `"summary"` | `"notes"` | `"conversation"` | `"comparison"`

**Response:** File download (Markdown)

