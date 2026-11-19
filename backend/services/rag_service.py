"""Complete RAG pipeline orchestration service."""
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Optional
from extensions import db

logger = logging.getLogger(__name__)


def process_document(app, document_id: str):
    """
    Full document processing pipeline:
    1. Extract text page-by-page
    2. Chunk text
    3. Generate embeddings
    4. Build FAISS index
    5. Update database
    """
    with app.app_context():
        from extensions import db
        from models.models import Document, DocumentChunk, ProcessingJob
        from services.pdf_service import extract_text_by_page, attempt_ocr
        from services.chunking_service import chunk_pages
        from services.embedding_service import embed_texts
        from services.vector_store import build_index

        doc = db.session.get(Document, document_id)
        if not doc:
            logger.error(f'Document {document_id} not found')
            return

        job = ProcessingJob.query.filter_by(document_id=document_id).order_by(
            ProcessingJob.created_at.desc()
        ).first()

        try:
            doc.status = 'processing'
            doc.processing_started_at = datetime.now(timezone.utc)
            doc.error_message = None
            db.session.commit()

            if job:
                job.status = 'running'
                job.started_at = datetime.now(timezone.utc)
                job.progress = 10
                db.session.commit()

            # Step 1: Extract text
            logger.info(f'Extracting text from {doc.file_path}')
            pages = extract_text_by_page(doc.file_path)

            # If scanned, try OCR
            total_words = sum(p.get('word_count', 0) for p in pages)
            if total_words < 100 and doc.total_pages and doc.total_pages > 0:
                logger.info(f'Low text count ({total_words} words), attempting OCR...')
                try:
                    pages = attempt_ocr(doc.file_path)
                    doc.is_scanned = True
                except Exception as ocr_err:
                    logger.warning(f'OCR failed: {ocr_err}')

            if job:
                job.progress = 30
                db.session.commit()

            # Step 2: Chunk text
            chunk_size = int(os.environ.get('CHUNK_SIZE', 1000))
            chunk_overlap = int(os.environ.get('CHUNK_OVERLAP', 200))
            chunks = chunk_pages(pages, document_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

            if not chunks:
                raise ValueError('No text could be extracted from this PDF')

            logger.info(f'Created {len(chunks)} chunks for document {document_id}')

            if job:
                job.progress = 50
                db.session.commit()

            # Step 3: Generate embeddings
            embedding_model = os.environ.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
            texts = [c['content'] for c in chunks]
            embeddings = embed_texts(texts, model_name=embedding_model)

            if job:
                job.progress = 70
                db.session.commit()

            # Step 4: Store chunks in DB
            # Clear existing chunks
            DocumentChunk.query.filter_by(document_id=document_id).delete()
            db.session.flush()

            db_chunks = []
            chunk_ids = []
            for i, (chunk, _) in enumerate(zip(chunks, embeddings)):
                db_chunk = DocumentChunk(
                    id=chunk['chunk_id'],
                    document_id=document_id,
                    chunk_index=chunk['chunk_index'],
                    content=chunk['content'],
                    page_number=chunk.get('page_number'),
                    page_range_start=chunk.get('page_range_start'),
                    page_range_end=chunk.get('page_range_end'),
                    char_start=chunk.get('char_start'),
                    char_end=chunk.get('char_end'),
                    faiss_index_id=i,
                )
                db_chunks.append(db_chunk)
                chunk_ids.append(chunk['chunk_id'])

            db.session.bulk_save_objects(db_chunks)
            db.session.flush()

            # Step 5: Build FAISS index
            faiss_folder = app.config.get('FAISS_FOLDER', 'storage/faiss_indexes')
            import numpy as np
            embeddings_array = embeddings.astype(np.float32)
            build_index(embeddings_array, chunk_ids, document_id, faiss_folder)

            if job:
                job.progress = 90
                db.session.commit()

            # Update document
            doc.status = 'ready'
            doc.chunk_count = len(chunks)
            doc.embedding_model = embedding_model
            doc.processing_completed_at = datetime.now(timezone.utc)
            db.session.commit()

            if job:
                job.status = 'done'
                job.progress = 100
                job.completed_at = datetime.now(timezone.utc)
                db.session.commit()

            logger.info(f'Document {document_id} processed successfully: {len(chunks)} chunks')

        except Exception as e:
            logger.error(f'Error processing document {document_id}: {e}', exc_info=True)
            try:
                doc = db.session.get(Document, document_id)
                if doc:
                    doc.status = 'failed'
                    doc.error_message = str(e)[:1000]
                    db.session.commit()
                if job:
                    job.status = 'failed'
                    job.error_message = str(e)[:1000]
                    job.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
            except Exception as db_err:
                logger.error(f'Failed to update error status: {db_err}')


def process_document_async(app, document_id: str):
    """Start document processing in a background thread."""
    thread = threading.Thread(
        target=process_document,
        args=(app, document_id),
        daemon=True,
        name=f'process-{document_id[:8]}',
    )
    thread.start()
    return thread


def retrieve_relevant_chunks(
    question: str,
    document_ids: list[str],
    db_session=None,
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2',
    faiss_folder: str = 'storage/faiss_indexes',
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a question from the given documents.
    Returns enriched chunk dicts including page numbers and content.
    """
    from services.embedding_service import embed_query
    from services.vector_store import search_multiple_documents
    from models.models import DocumentChunk, Document

    session = db_session if db_session is not None else db.session

    query_emb = embed_query(question, model_name=embedding_model)

    # Search FAISS
    raw_results = search_multiple_documents(
        query_emb, document_ids, faiss_folder, top_k=top_k
    )

    if not raw_results:
        return []

    # Enrich with DB data
    enriched = []
    for result in raw_results:
        chunk = session.get(DocumentChunk, result['chunk_id'])
        if not chunk:
            continue
        doc = session.get(Document, chunk.document_id)
        enriched.append({
            'chunk_id': chunk.id,
            'document_id': chunk.document_id,
            'document_title': doc.title if doc else 'Unknown',
            'content': chunk.content,
            'page_number': chunk.page_number,
            'page_range_start': chunk.page_range_start,
            'page_range_end': chunk.page_range_end,
            'score': result['score'],
        })

    return enriched

