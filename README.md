# 🎓 Scholar AI — Research Paper Assistant

**Scholar AI** is a full-stack AI-powered research assistant that lets you upload academic PDF papers, ask natural-language questions, get grounded answers with **page-level citations**, generate structured summaries, compare multiple papers, and extract research insights — all powered by **Google Gemini + RAG (Retrieval-Augmented Generation)**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 PDF Upload & Processing | Upload any PDF; text is extracted page-by-page via PyMuPDF |
| 🔍 Semantic Search | FAISS vector index + Sentence Transformers for relevance retrieval |
| 🤖 RAG Q&A | Gemini-powered answers grounded in document evidence |
| 📌 Page Citations | Every answer includes clickable page-level source references |
| 📋 Summarization | Short / Detailed / Section-by-Section structured summaries |
| ⚖️ Paper Comparison | AI comparison of 2+ papers across methodology, results, gaps |
| 💡 Insights Extraction | Research themes, key findings, terminology, research gaps |
| 📝 Notes | Create, edit, delete notes linked to document pages |
| 📚 Collections | Organise papers into named collections |
| 💬 Conversation History | All chats persisted in SQLite with full context restoration |
| 🌙 Obsidian Dark UI | Premium dark interface with responsive design |
| 📱 Responsive | Works on desktop (3-column), tablet, and mobile |

---

## 🗂️ Project Structure

```
scholar-ai/
├── frontend/
│   ├── index.html          # Single-page application shell
│   ├── css/
│   │   ├── styles.css      # Obsidian Dark design system
│   │   ├── components.css  # Shared components
│   │   └── responsive.css  # Breakpoints 1440→390px
│   └── js/
│       ├── api.js          # Backend API client
│       ├── app.js          # Bootstrap & Home module
│       ├── navigation.js   # Routing, sidebar, upload modal, toasts
│       ├── pdf-viewer.js   # PDF.js integration
│       ├── chat.js         # AI chat workspace
│       ├── documents.js    # Document card components
│       ├── library.js      # Research library page
│       ├── comparison.js   # Multi-paper comparison
│       ├── summaries.js    # Summarization page
│       ├── insights.js     # Insights page + PDF panel tab
│       ├── notes.js        # Notes panel
│       └── settings.js     # Settings page
│
├── backend/
│   ├── run.py              # Entry point
│   ├── app.py              # Flask application factory
│   ├── config.py           # Environment configuration
│   ├── extensions.py       # SQLAlchemy, CORS
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # ← Add your GEMINI_API_KEY here
│   ├── .env.example        # Environment template
│   │
│   ├── models/
│   │   └── models.py       # SQLAlchemy ORM models
│   ├── routes/
│   │   ├── health.py       # /api/v1/health
│   │   ├── documents.py    # /api/v1/documents
│   │   ├── chat.py         # /api/v1/chat, /api/v1/conversations
│   │   ├── research.py     # /api/v1/compare, summaries, insights
│   │   ├── notes.py        # /api/v1/notes, /api/v1/collections
│   │   └── exports.py      # /api/v1/exports
│   ├── services/
│   │   ├── pdf_service.py      # PyMuPDF extraction & metadata
│   │   ├── chunking_service.py # Sentence-aware text chunking
│   │   ├── embedding_service.py # Sentence Transformers
│   │   ├── vector_store.py     # FAISS index management
│   │   ├── gemini_service.py   # Google Gemini API client
│   │   └── rag_service.py      # RAG pipeline orchestration
│   ├── database/
│   │   └── __init__.py         # DB initialization
│   ├── storage/
│   │   ├── uploads/            # Uploaded PDF files
│   │   └── faiss_indexes/      # Persisted FAISS indexes
│   └── tests/
│       └── test_scholar_ai.py  # Pytest test suite
│
└── docs/
    ├── API.md              # API reference
    ├── ARCHITECTURE.md     # System architecture
    └── USER_GUIDE.md       # End-user guide
```

---

## 🚀 Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.11+
- pip
- A Google Gemini API key → [Get one here](https://aistudio.google.com/apikey)
- VS Code with Live Server extension (for frontend)

### 1. Set Up the Backend

```powershell
# Navigate to project
cd "C:\Users\hr210\OneDrive\Desktop\NLP Project\scholar-ai\backend"

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies (takes 2-5 minutes — downloads ML models)
pip install -r requirements.txt

# Configure environment
copy .env.example .env
notepad .env
# → Set GEMINI_API_KEY=your_actual_key_here

# Start the backend
python run.py
```

Backend starts at: **http://127.0.0.1:5000**

### 2. Serve the Frontend

**Option A — VS Code Live Server (recommended)**
1. Install the [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) extension
2. Open `frontend/index.html` in VS Code
3. Click **Go Live** in the status bar → opens at **http://127.0.0.1:5500**

**Option B — Python HTTP server**
```powershell
cd "C:\Users\hr210\OneDrive\Desktop\NLP Project\scholar-ai\frontend"
python -m http.server 5500
# Open http://localhost:5500
```

> ⚠️ **Do not** open `index.html` directly via `file://` — the PDF viewer and API calls require HTTP.

---

## 🔑 Gemini API Setup

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create an API key
3. Add it to `backend/.env`:
   ```
   GEMINI_API_KEY=your_actual_key_here
   GEMINI_MODEL=gemini-1.5-flash
   ```
4. Restart the Flask server

The API key is **never exposed to the browser** — all Gemini calls go through the Flask backend.

---

## 🧪 Running Tests

```powershell
cd "C:\Users\hr210\OneDrive\Desktop\NLP Project\scholar-ai\backend"
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

To run live Gemini tests (requires real API key):
```powershell
$env:GEMINI_API_KEY="your_actual_key"
pytest tests/ -v -k "LiveGemini"
```

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | **Required.** Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence Transformers model |
| `CHUNK_SIZE` | `1000` | Characters per text chunk |
| `CHUNK_OVERLAP` | `200` | Character overlap between chunks |
| `TOP_K_RETRIEVAL` | `5` | Top-k chunks retrieved per query |
| `MAX_CONTENT_LENGTH` | `52428800` | Max upload size (50MB) |
| `DATABASE_URL` | `sqlite:///scholar_ai.db` | SQLite path |

---

## 🌐 API Endpoints Summary

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/health/ready` | Readiness + dependency check |
| POST | `/api/v1/documents` | Upload PDF |
| GET | `/api/v1/documents` | List documents |
| GET | `/api/v1/documents/<id>` | Get document |
| DELETE | `/api/v1/documents/<id>` | Delete document |
| GET | `/api/v1/documents/<id>/status` | Processing status |
| POST | `/api/v1/documents/<id>/retry` | Retry failed processing |
| GET | `/api/v1/documents/<id>/pdf` | Serve PDF file |
| GET | `/api/v1/documents/<id>/pages/<n>` | Get page chunks |
| POST | `/api/v1/conversations` | Create conversation |
| GET | `/api/v1/conversations` | List conversations |
| GET | `/api/v1/conversations/<id>` | Get with messages |
| PATCH | `/api/v1/conversations/<id>` | Rename/update |
| DELETE | `/api/v1/conversations/<id>` | Delete |
| POST | `/api/v1/chat` | RAG chat (main AI endpoint) |
| POST | `/api/v1/documents/<id>/summaries` | Generate summary |
| POST | `/api/v1/compare` | Compare papers |
| GET/POST | `/api/v1/documents/<id>/insights` | Get/generate insights |
| GET | `/api/v1/search` | Semantic/keyword search |
| GET | `/api/v1/stats` | Application statistics |
| GET/POST | `/api/v1/notes` | List/create notes |
| PATCH/DELETE | `/api/v1/notes/<id>` | Update/delete note |
| GET/POST | `/api/v1/collections` | List/create collections |
| PATCH/DELETE | `/api/v1/collections/<id>` | Update/delete |
| POST | `/api/v1/exports` | Export summary/notes/comparison |

---

## 🏗️ Architecture Overview

```
Browser (Vanilla JS + PDF.js)
        │ HTTP REST
        ▼
Flask Backend (Python 3.11)
    ├── Routes (Blueprint per feature)
    ├── Services
    │   ├── pdf_service      → PyMuPDF text extraction
    │   ├── chunking_service → Sentence-aware chunking
    │   ├── embedding_service → Sentence Transformers (local)
    │   ├── vector_store     → FAISS CPU index management
    │   ├── gemini_service   → Google Gemini API (RAG answers)
    │   └── rag_service      → Pipeline orchestration
    └── Database
        ├── SQLite (SQLAlchemy ORM)
        │   └── Documents, Chunks, Conversations, Messages,
        │       Summaries, Notes, Collections, Insights
        └── FAISS indexes (per-document .index files)
```

---

## ⚠️ Known Limitations

1. **Single-user**: No authentication. Designed for local/personal use.
2. **Scanned PDFs**: OCR support requires Tesseract installed separately.
3. **Large papers**: Very large PDFs (500+ pages) may take 2-5 minutes to process.
4. **Gemini quota**: Subject to Google AI Studio rate limits on free tier.
5. **Streaming**: Real-time streaming responses not implemented (full response returned).

---

## 📄 License

MIT License — For educational and research use.

---

*Scholar AI — Built for BCA Final Year Project, Academic Evaluation, and GitHub Portfolio.*

