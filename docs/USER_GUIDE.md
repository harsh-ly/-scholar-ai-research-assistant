# Scholar AI User Guide

## Getting Started

### 1. Upload Your First Paper
Click **Upload Paper** from the Home page or the sidebar.
- Drag & drop or click to browse for a PDF (max 50 MB).
- Scholar AI automatically extracts the title, authors, and year.
- Processing (chunking + embedding) runs in the background — watch the status dot turn green.

### 2. Ask Questions
- Navigate to **Chats** and click **Select Paper** (book icon).
- Pick your uploaded, ready paper.
- Type your question and press **Enter**.

**Example questions:**
- "What methodology did the authors use?"
- "Summarize the main contributions."
- "What datasets were used in the experiments?"
- "What are the limitations acknowledged?"

Citations appear as clickable chips below each answer. Click a chip to jump to that page in the PDF viewer.

### 3. Summarize a Paper
- Go to **Summarize** in the sidebar.
- Select your paper and choose summary length (Short / Detailed / Section-by-Section).
- Click **Generate** — Gemini produces a structured summary.
- Use **Copy** or **Download** to export as Markdown.

### 4. Compare Papers
- Upload at least 2 papers and wait for both to finish processing.
- Go to **Compare Papers**.
- Select 2 or more papers (click to highlight).
- Click **Generate Comparison**.
- Results include methodology, results, common themes, research gaps, and synthesis.

### 5. Extract Insights
- Go to **Insights**.
- Select a paper and click **Generate Insights**.
- Results include research themes, key concepts, findings, terminology, methodology insights, and potential research gaps.

### 6. Take Notes
- While viewing a PDF, switch to the **Notes** tab in the right panel.
- Click **New Note** to create a note (automatically linked to the current page).
- Notes are saved to the database and associated with the document.

### 7. Keyboard Shortcuts
| Shortcut | Action |
|---|---|
| Ctrl+K | New chat |
| Ctrl+U | Upload paper |
| Enter | Send message |
| Shift+Enter | New line in message |
| Escape | Close modal / dropdown |

---

## Tips

- **Processing time**: Large papers (100+ pages) may take 1-3 minutes to process.
- **Best questions**: Specific, document-grounded questions get the best answers.
- **Scanned PDFs**: If Scholar AI reports low text, the PDF may be image-based. OCR support requires Tesseract.
- **API quota**: The free Google AI Studio tier has rate limits. If you hit a quota error, wait 60 seconds and retry.
- **Follow-up questions**: After each AI answer, click any of the suggested follow-up questions for instant continuation.

---

## Troubleshooting

**"Cannot reach backend"**
→ Make sure Flask is running: `cd backend && python run.py`

**"Document processing failed"**
→ Click **Retry** on the document card. Check that the PDF is not encrypted or corrupted.

**"Gemini API key not configured"**
→ Add your key to `backend/.env` and restart Flask.

**"No ready documents"**
→ Wait for processing to complete (watch for the green dot in the library).

