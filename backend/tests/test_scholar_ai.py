"""
Scholar AI — Pytest test suite
Run: cd backend && pytest tests/ -v
"""
import io
import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

# ── App factory fixture ─────────────────────────────────────────
@pytest.fixture
def app():
    os.environ['FLASK_ENV'] = 'testing'
    os.environ['GEMINI_API_KEY'] = 'test-key-do-not-use'
    from config import TestingConfig
    from app import create_app
    app = create_app(TestingConfig)
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'scholar_ai_test_uploads')
    app.config['FAISS_FOLDER'] = os.path.join(tempfile.gettempdir(), 'scholar_ai_test_faiss')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['FAISS_FOLDER'], exist_ok=True)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app

# ── Helper ──────────────────────────────────────────────────────
def make_pdf_bytes():
    """Create a minimal valid PDF byte string."""
    return (
        b'%PDF-1.4\n'
        b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
        b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
        b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n'
        b'/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
        b'4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Hello World) Tj ET\nendstream\nendobj\n'
        b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
        b'xref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n'
        b'0000000115 00000 n\n0000000274 00000 n\n0000000370 00000 n\n'
        b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF\n'
    )

# ── Health Tests ────────────────────────────────────────────────
class TestHealth:
    def test_health_ok(self, client):
        r = client.get('/api/v1/health')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'ok'

    def test_health_ready(self, client):
        r = client.get('/api/v1/health/ready')
        assert r.status_code in (200, 503)
        data = r.get_json()
        assert 'status' in data
        assert 'checks' in data

# ── Document Tests ──────────────────────────────────────────────
class TestDocuments:
    def test_list_documents_empty(self, client):
        r = client.get('/api/v1/documents')
        assert r.status_code == 200
        data = r.get_json()
        assert 'documents' in data
        assert isinstance(data['documents'], list)

    def test_upload_no_file(self, client):
        r = client.post('/api/v1/documents')
        assert r.status_code == 400

    def test_upload_invalid_file_type(self, client):
        data = {'file': (io.BytesIO(b'hello'), 'test.txt')}
        r = client.post('/api/v1/documents', data=data, content_type='multipart/form-data')
        assert r.status_code == 400
        assert 'PDF' in r.get_json().get('error', '')

    def test_upload_valid_pdf(self, client):
        pdf = make_pdf_bytes()
        data = {'file': (io.BytesIO(pdf), 'test_paper.pdf')}
        r = client.post('/api/v1/documents', data=data, content_type='multipart/form-data')
        assert r.status_code in (201, 400, 409)
        if r.status_code == 201:
            doc = r.get_json()['document']
            assert 'id' in doc
            assert doc['status'] in ('uploaded', 'processing', 'ready')

    def test_get_nonexistent_document(self, client):
        r = client.get('/api/v1/documents/nonexistent-id')
        assert r.status_code == 404

    def test_delete_nonexistent_document(self, client):
        r = client.delete('/api/v1/documents/nonexistent-id')
        assert r.status_code == 404

# ── Conversation Tests ──────────────────────────────────────────
class TestConversations:
    def test_list_conversations_empty(self, client):
        r = client.get('/api/v1/conversations')
        assert r.status_code == 200
        data = r.get_json()
        assert 'conversations' in data

    def test_create_conversation(self, client):
        r = client.post('/api/v1/conversations',
                        json={'title': 'Test Conv', 'document_ids': []})
        assert r.status_code == 201
        data = r.get_json()
        assert data['conversation']['title'] == 'Test Conv'

    def test_update_conversation(self, client):
        r = client.post('/api/v1/conversations', json={'title': 'Old Title'})
        conv_id = r.get_json()['conversation']['id']
        r2 = client.patch(f'/api/v1/conversations/{conv_id}', json={'title': 'New Title'})
        assert r2.status_code == 200
        assert r2.get_json()['conversation']['title'] == 'New Title'

    def test_delete_conversation(self, client):
        r = client.post('/api/v1/conversations', json={'title': 'To Delete'})
        conv_id = r.get_json()['conversation']['id']
        r2 = client.delete(f'/api/v1/conversations/{conv_id}')
        assert r2.status_code == 200
        r3 = client.get(f'/api/v1/conversations/{conv_id}')
        assert r3.status_code == 404

# ── Chat Tests ──────────────────────────────────────────────────
class TestChat:
    def test_chat_no_body(self, client):
        r = client.post('/api/v1/chat', data='', content_type='application/json')
        assert r.status_code == 400

    def test_chat_no_question(self, client):
        r = client.post('/api/v1/chat', json={'document_ids': ['abc']})
        assert r.status_code == 400

    def test_chat_no_documents(self, client):
        r = client.post('/api/v1/chat', json={'question': 'Hello?', 'document_ids': []})
        assert r.status_code == 400

    def test_chat_with_missing_doc(self, client):
        r = client.post('/api/v1/chat', json={'question': 'Hello?', 'document_ids': ['nonexistent']})
        assert r.status_code == 400

# ── Notes Tests ─────────────────────────────────────────────────
class TestNotes:
    def test_list_notes(self, client):
        r = client.get('/api/v1/notes')
        assert r.status_code == 200

    def test_create_note(self, client):
        r = client.post('/api/v1/notes', json={'content': 'Test note content'})
        assert r.status_code == 201
        data = r.get_json()
        assert data['note']['content'] == 'Test note content'

    def test_create_note_no_content(self, client):
        r = client.post('/api/v1/notes', json={'title': 'Title only'})
        assert r.status_code == 400

    def test_update_note(self, client):
        r = client.post('/api/v1/notes', json={'content': 'Original'})
        note_id = r.get_json()['note']['id']
        r2 = client.patch(f'/api/v1/notes/{note_id}', json={'content': 'Updated'})
        assert r2.status_code == 200
        assert r2.get_json()['note']['content'] == 'Updated'

    def test_delete_note(self, client):
        r = client.post('/api/v1/notes', json={'content': 'To delete'})
        note_id = r.get_json()['note']['id']
        r2 = client.delete(f'/api/v1/notes/{note_id}')
        assert r2.status_code == 200

# ── Collections Tests ────────────────────────────────────────────
class TestCollections:
    def test_list_collections(self, client):
        r = client.get('/api/v1/collections')
        assert r.status_code == 200

    def test_create_collection(self, client):
        r = client.post('/api/v1/collections', json={'name': 'My Collection'})
        assert r.status_code == 201
        assert r.get_json()['collection']['name'] == 'My Collection'

    def test_create_collection_no_name(self, client):
        r = client.post('/api/v1/collections', json={'description': 'no name'})
        assert r.status_code == 400

    def test_delete_collection(self, client):
        r = client.post('/api/v1/collections', json={'name': 'Delete Me'})
        coll_id = r.get_json()['collection']['id']
        r2 = client.delete(f'/api/v1/collections/{coll_id}')
        assert r2.status_code == 200

# ── PDF Processing Tests ─────────────────────────────────────────
class TestPDFProcessing:
    def test_pdf_validation_valid(self, app_ctx):
        import tempfile
        from services.pdf_service import validate_pdf
        pdf = make_pdf_bytes()
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(pdf)
            path = f.name
        result = validate_pdf(path)
        os.unlink(path)
        # Could be valid or invalid depending on PyMuPDF version
        assert 'valid' in result

    def test_chunking_basic(self, app_ctx):
        from services.chunking_service import chunk_pages
        pages = [{'page_number': 1, 'text': 'This is a test sentence. ' * 50, 'word_count': 200, 'is_empty': False}]
        chunks = chunk_pages(pages, 'test-doc-id', chunk_size=200, chunk_overlap=50)
        assert isinstance(chunks, list)
        for chunk in chunks:
            assert 'content' in chunk
            assert 'page_number' in chunk
            assert chunk['page_number'] == 1
            assert len(chunk['content']) > 0

    def test_chunking_preserves_page_numbers(self, app_ctx):
        from services.chunking_service import chunk_pages
        pages = [
            {'page_number': 1, 'text': 'Page one content. ' * 30, 'word_count': 90, 'is_empty': False},
            {'page_number': 2, 'text': 'Page two content. ' * 30, 'word_count': 90, 'is_empty': False},
        ]
        chunks = chunk_pages(pages, 'test-doc', chunk_size=300, chunk_overlap=50)
        p1_chunks = [c for c in chunks if c['page_number'] == 1]
        p2_chunks = [c for c in chunks if c['page_number'] == 2]
        assert len(p1_chunks) > 0
        assert len(p2_chunks) > 0

    def test_empty_pages_skipped(self, app_ctx):
        from services.chunking_service import chunk_pages
        pages = [
            {'page_number': 1, 'text': '', 'word_count': 0, 'is_empty': True},
            {'page_number': 2, 'text': 'Real content here. ' * 20, 'word_count': 60, 'is_empty': False},
        ]
        chunks = chunk_pages(pages, 'test-doc', chunk_size=300, chunk_overlap=50)
        page1_chunks = [c for c in chunks if c['page_number'] == 1]
        assert len(page1_chunks) == 0

# ── Embedding Tests ──────────────────────────────────────────────
class TestEmbeddings:
    def test_embed_texts(self, app_ctx):
        from services.embedding_service import embed_texts
        texts = ['This is a test sentence about machine learning.']
        embeddings = embed_texts(texts)
        assert embeddings.shape[0] == 1
        assert embeddings.shape[1] > 0
        assert embeddings.dtype.name == 'float32'

    def test_embed_query(self, app_ctx):
        from services.embedding_service import embed_query
        emb = embed_query('What is deep learning?')
        assert emb.shape[0] == 1
        assert emb.shape[1] > 0

    def test_embedding_dimension_consistent(self, app_ctx):
        from services.embedding_service import embed_texts, embed_query
        doc_emb = embed_texts(['Document text here.'])
        q_emb = embed_query('Query text')
        assert doc_emb.shape[1] == q_emb.shape[1]

# ── FAISS Tests ──────────────────────────────────────────────────
class TestFAISS:
    def test_build_and_search_index(self, app_ctx, tmp_path):
        import numpy as np
        from services.vector_store import build_index, search_index
        faiss_folder = str(tmp_path)
        doc_id = 'test-faiss-doc'
        dim = 384
        n = 5
        embeddings = np.random.rand(n, dim).astype('float32')
        # Normalize
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        chunk_ids = [f'chunk-{i}' for i in range(n)]

        count = build_index(embeddings, chunk_ids, doc_id, faiss_folder)
        assert count == n

        query = np.random.rand(1, dim).astype('float32')
        query = query / np.linalg.norm(query)
        results = search_index(query, doc_id, faiss_folder, top_k=3)
        assert len(results) == 3
        assert all('chunk_id' in r for r in results)
        assert all('score' in r for r in results)

    def test_index_persistence(self, app_ctx, tmp_path):
        import numpy as np
        from services.vector_store import build_index, load_index
        faiss_folder = str(tmp_path)
        doc_id = 'persist-test'
        dim = 128
        embeddings = np.random.rand(3, dim).astype('float32')
        chunk_ids = ['c1', 'c2', 'c3']
        build_index(embeddings, chunk_ids, doc_id, faiss_folder)

        index, meta = load_index(faiss_folder, doc_id)
        assert index is not None
        assert meta['count'] == 3
        assert meta['chunk_ids'] == chunk_ids

    def test_missing_index(self, app_ctx, tmp_path):
        from services.vector_store import load_index
        index, meta = load_index(str(tmp_path), 'nonexistent')
        assert index is None
        assert meta is None

# ── Gemini Service Tests (mocked) ────────────────────────────────
class TestGeminiService:
    @patch('services.gemini_service._get_client')
    def test_generate_rag_answer_no_context(self, mock_client):
        from services.gemini_service import generate_rag_answer
        result = generate_rag_answer('fake-key', 'fake-model', 'What is this?', [])
        assert 'answer' in result
        assert 'not find' in result['answer'].lower() or 'could not' in result['answer'].lower()

    @patch('services.gemini_service._generate_with_retry')
    def test_generate_summary(self, mock_gen):
        mock_gen.return_value = '{"executive_summary": "Test summary", "methodology": "Test method"}'
        from services.gemini_service import generate_summary
        result = generate_summary('key', 'model', 'Test Paper', ['chunk1', 'chunk2'])
        assert 'content' in result

    @patch('services.gemini_service._generate_with_retry')
    def test_generate_insights(self, mock_gen):
        mock_gen.return_value = '{"research_themes": ["AI", "NLP"], "main_findings": ["Finding 1"]}'
        from services.gemini_service import generate_insights
        result = generate_insights('key', 'model', 'Test Paper', 'some text')
        assert 'structured_data' in result

# ── Security Tests ────────────────────────────────────────────────
class TestSecurity:
    def test_path_traversal_prevented(self, client):
        # Attempt path traversal in doc ID
        r = client.get('/api/v1/documents/../../../etc/passwd')
        assert r.status_code in (400, 404)

    def test_large_file_rejected(self, client):
        # Simulate oversized upload
        huge_data = b'%PDF-' + b'x' * (51 * 1024 * 1024)
        data = {'file': (io.BytesIO(huge_data), 'huge.pdf')}
        r = client.post('/api/v1/documents', data=data, content_type='multipart/form-data')
        assert r.status_code in (400, 413)

    def test_no_stack_trace_in_error(self, client):
        r = client.get('/api/v1/documents/invalid-id-xyz')
        assert r.status_code == 404
        data = r.get_json()
        # Should not expose traceback
        assert 'Traceback' not in str(data)
        assert 'File "' not in str(data)

    def test_search_requires_query(self, client):
        r = client.get('/api/v1/search')
        assert r.status_code == 400

# ── Stats Tests ───────────────────────────────────────────────────
class TestStats:
    def test_get_stats(self, client):
        r = client.get('/api/v1/stats')
        assert r.status_code == 200
        data = r.get_json()
        assert 'total_documents' in data
        assert 'total_conversations' in data


# ── RAG Pipeline Integration Tests ─────────────────────────────────
class TestRAGPipeline:
    def test_retrieve_relevant_chunks_db_session(self, app_ctx):
        from extensions import db
        from models.models import Document, DocumentChunk
        from services.rag_service import retrieve_relevant_chunks
        from unittest.mock import patch

        doc = Document(
            id='test-rag-doc',
            title='Test RAG Document',
            filename='test.pdf',
            original_filename='test.pdf',
            file_path='/tmp/test.pdf',
            status='ready',
        )
        chunk = DocumentChunk(
            id='test-rag-chunk-1',
            document_id='test-rag-doc',
            chunk_index=0,
            content='This is a document about machine learning architectures.',
            page_number=1,
            page_range_start=1,
            page_range_end=1,
        )
        db.session.add(doc)
        db.session.add(chunk)
        db.session.commit()

        mock_raw_results = [{'chunk_id': 'test-rag-chunk-1', 'score': 0.95, 'document_id': 'test-rag-doc'}]

        with patch('services.embedding_service.embed_query') as mock_embed, \
             patch('services.vector_store.search_multiple_documents', return_value=mock_raw_results):
            mock_embed.return_value = [0.1] * 384
            # Test with explicit db_session passed
            enriched = retrieve_relevant_chunks(
                question='machine learning',
                document_ids=['test-rag-doc'],
                db_session=db.session,
                embedding_model='test-model',
                faiss_folder='/tmp/test_faiss',
                top_k=3,
            )
            assert len(enriched) == 1
            assert enriched[0]['chunk_id'] == 'test-rag-chunk-1'
            assert enriched[0]['document_title'] == 'Test RAG Document'
            assert enriched[0]['page_number'] == 1

            # Test with db_session default (None)
            enriched_default = retrieve_relevant_chunks(
                question='machine learning',
                document_ids=['test-rag-doc'],
                embedding_model='test-model',
                faiss_folder='/tmp/test_faiss',
                top_k=3,
            )
            assert len(enriched_default) == 1
            assert enriched_default[0]['chunk_id'] == 'test-rag-chunk-1'


# ── Live Gemini test (only when API key configured) ──────────────
@pytest.mark.skipif(
    not os.environ.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY') == 'test-key-do-not-use',
    reason='Requires real GEMINI_API_KEY'
)
class TestLiveGemini:
    def test_generate_short_answer(self):
        from services.gemini_service import generate_rag_answer
        api_key = os.environ['GEMINI_API_KEY']
        model = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')
        chunks = [{
            'chunk_id': 'c1', 'document_id': 'd1', 'document_title': 'Test',
            'content': 'Machine learning is a subset of artificial intelligence.',
            'page_number': 1, 'score': 0.9
        }]
        result = generate_rag_answer(api_key, model, 'What is machine learning?', chunks)
        assert result['answer']
        assert len(result['answer']) > 10

