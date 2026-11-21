"""Document management routes."""
import os
import hashlib
import logging
import uuid
from flask import Blueprint, request, jsonify, current_app, send_file, abort
from werkzeug.utils import secure_filename
from extensions import db
from models.models import Document, DocumentChunk, ProcessingJob

logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


def compute_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


@documents_bp.route('', methods=['POST'])
def upload_document():
    """Upload and process a PDF document."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'Empty file upload'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are supported'}), 400

    # Secure and save file
    original_filename = file.filename
    safe_name = secure_filename(original_filename)
    if not safe_name:
        safe_name = 'document.pdf'

    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'storage/uploads')
    os.makedirs(upload_folder, exist_ok=True)

    doc_id = str(uuid.uuid4())
    stored_filename = f'{doc_id}_{safe_name}'
    file_path = os.path.join(upload_folder, stored_filename)

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500

    # Check file size
    file_size = os.path.getsize(file_path)
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 52428800)
    if file_size > max_size:
        os.remove(file_path)
        return jsonify({'error': f'File too large. Maximum size is {max_size // (1024*1024)}MB'}), 413

    # Validate PDF
    from services.pdf_service import validate_pdf
    validation = validate_pdf(file_path)
    if not validation['valid']:
        os.remove(file_path)
        return jsonify({'error': validation['error']}), 400

    # Compute hash to detect duplicates
    file_hash = compute_hash(file_path)
    existing = Document.query.filter_by(file_hash=file_hash).first()
    if existing:
        os.remove(file_path)
        return jsonify({
            'error': 'This document has already been uploaded',
            'existing_document': existing.to_dict(),
        }), 409

    # Extract metadata
    from services.pdf_service import extract_pdf_metadata
    metadata = extract_pdf_metadata(file_path)

    # Create document record
    title = request.form.get('title') or metadata.get('title') or os.path.splitext(original_filename)[0]
    doc = Document(
        id=doc_id,
        title=title[:500],
        filename=stored_filename,
        original_filename=original_filename[:500],
        file_hash=file_hash,
        file_size=file_size,
        file_path=file_path,
        authors=metadata.get('authors'),
        publication_year=metadata.get('publication_year'),
        total_pages=metadata.get('total_pages'),
        abstract=metadata.get('abstract'),
        is_scanned=metadata.get('is_scanned', False),
        status='uploaded',
    )
    db.session.add(doc)

    # Create processing job
    job = ProcessingJob(document_id=doc_id, job_type='full_processing', status='pending')
    db.session.add(job)
    db.session.commit()

    # Start async processing
    from services.rag_service import process_document_async
    process_document_async(current_app._get_current_object(), doc_id)

    return jsonify({
        'message': 'Document uploaded successfully, processing started',
        'document': doc.to_dict(),
    }), 201


@documents_bp.route('', methods=['GET'])
def list_documents():
    """List all documents with optional filtering."""
    status_filter = request.args.get('status')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'created_at')
    order = request.args.get('order', 'desc')

    query = Document.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(Document.title.ilike(f'%{search}%'))

    sort_col = getattr(Document, sort_by, Document.created_at)
    if order == 'asc':
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    docs = query.all()
    return jsonify({'documents': [d.to_dict() for d in docs], 'total': len(docs)}), 200


@documents_bp.route('/<doc_id>', methods=['GET'])
def get_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    return jsonify({'document': doc.to_dict()}), 200


@documents_bp.route('/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)

    # Delete FAISS index
    try:
        from services.vector_store import delete_index
        faiss_folder = current_app.config.get('FAISS_FOLDER', 'storage/faiss_indexes')
        delete_index(faiss_folder, doc_id)
    except Exception as e:
        logger.warning(f'Failed to delete FAISS index: {e}')

    # Delete file
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f'Failed to delete file: {e}')

    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted successfully'}), 200


@documents_bp.route('/<doc_id>/status', methods=['GET'])
def get_document_status(doc_id):
    doc = Document.query.get_or_404(doc_id)
    job = ProcessingJob.query.filter_by(document_id=doc_id).order_by(
        ProcessingJob.created_at.desc()
    ).first()
    return jsonify({
        'document_id': doc_id,
        'status': doc.status,
        'chunk_count': doc.chunk_count,
        'error_message': doc.error_message,
        'job': job.to_dict() if job else None,
    }), 200


@documents_bp.route('/<doc_id>/retry', methods=['POST'])
def retry_processing(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.status not in ('failed', 'uploaded'):
        return jsonify({'error': 'Document is not in a retryable state'}), 400

    job = ProcessingJob(document_id=doc_id, job_type='full_processing', status='pending')
    db.session.add(job)
    doc.status = 'uploaded'
    doc.error_message = None
    db.session.commit()

    from services.rag_service import process_document_async
    process_document_async(current_app._get_current_object(), doc_id)

    return jsonify({'message': 'Processing restarted', 'document': doc.to_dict()}), 200


@documents_bp.route('/<doc_id>/pdf', methods=['GET'])
def serve_pdf(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if not doc.file_path or not os.path.exists(doc.file_path):
        abort(404)
    return send_file(
        doc.file_path,
        mimetype='application/pdf',
        as_attachment=False,
        download_name=doc.original_filename,
    )


@documents_bp.route('/<doc_id>/pages/<int:page_num>', methods=['GET'])
def get_page_text(doc_id, page_num):
    doc = Document.query.get_or_404(doc_id)
    chunks = DocumentChunk.query.filter_by(
        document_id=doc_id, page_number=page_num
    ).all()
    if not chunks:
        return jsonify({'page_number': page_num, 'content': '', 'chunks': []}), 200
    return jsonify({
        'page_number': page_num,
        'chunks': [c.to_dict() for c in chunks],
    }), 200

