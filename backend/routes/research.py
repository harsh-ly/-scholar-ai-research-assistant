"""Research routes: summaries, comparisons, insights, search."""
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.models import Document, DocumentChunk, Summary, Insight

logger = logging.getLogger(__name__)
research_bp = Blueprint('research', __name__)


def _get_api_key():
    key = current_app.config.get('GEMINI_API_KEY', '')
    if not key or key == 'your_gemini_api_key_here':
        return None
    return key


@research_bp.route('/documents/<doc_id>/summaries', methods=['POST'])
def generate_summary(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.status != 'ready':
        return jsonify({'error': 'Document is not ready for analysis'}), 400

    api_key = _get_api_key()
    if not api_key:
        return jsonify({'error': 'Gemini API key not configured'}), 503

    data = request.get_json() or {}
    summary_type = data.get('summary_type', 'detailed')
    if summary_type not in ('short', 'detailed', 'section_wise'):
        summary_type = 'detailed'

    # Check for cached summary
    existing = Summary.query.filter_by(
        document_id=doc_id, summary_type=summary_type
    ).order_by(Summary.created_at.desc()).first()
    if existing and not data.get('regenerate'):
        return jsonify({'summary': existing.to_dict()}), 200

    # Get document chunks
    chunks = DocumentChunk.query.filter_by(document_id=doc_id).order_by(
        DocumentChunk.chunk_index
    ).all()
    texts = [c.content for c in chunks]

    if not texts:
        return jsonify({'error': 'No content found in document'}), 400

    try:
        model = current_app.config.get('GEMINI_MODEL', 'gemini-3.5-flash')
        from services.gemini_service import generate_summary as gemini_summary
        result = gemini_summary(api_key, model, doc.title, texts, summary_type)
    except Exception as e:
        logger.error(f'Summary generation failed: {e}', exc_info=True)
        return jsonify({'error': f'Summary generation failed: {str(e)[:200]}'}), 500

    summary = Summary(
        document_id=doc_id,
        summary_type=summary_type,
        content=result['content'],
        structured_data=json.dumps(result['structured_data']) if result.get('structured_data') else None,
    )
    db.session.add(summary)
    db.session.commit()

    return jsonify({'summary': summary.to_dict()}), 201


@research_bp.route('/compare', methods=['POST'])
def compare_papers():
    data = request.get_json() or {}
    document_ids = data.get('document_ids', [])

    if len(document_ids) < 2:
        return jsonify({'error': 'At least 2 documents required for comparison'}), 400

    api_key = _get_api_key()
    if not api_key:
        return jsonify({'error': 'Gemini API key not configured'}), 503

    docs = Document.query.filter(
        Document.id.in_(document_ids),
        Document.status == 'ready',
    ).all()

    if len(docs) < 2:
        return jsonify({'error': 'At least 2 ready documents required'}), 400

    papers = []
    for doc in docs:
        chunks = DocumentChunk.query.filter_by(document_id=doc.id).order_by(
            DocumentChunk.chunk_index
        ).limit(20).all()
        papers.append({
            'title': doc.title,
            'chunks': [c.content for c in chunks],
        })

    try:
        model = current_app.config.get('GEMINI_MODEL', 'gemini-3.5-flash')
        from services.gemini_service import generate_comparison
        result = generate_comparison(api_key, model, papers)
    except Exception as e:
        logger.error(f'Comparison failed: {e}', exc_info=True)
        return jsonify({'error': f'Comparison failed: {str(e)[:200]}'}), 500

    return jsonify({
        'document_ids': [d.id for d in docs],
        'documents': [{'id': d.id, 'title': d.title} for d in docs],
        'comparison': result.get('structured_data'),
        'raw': result.get('raw', ''),
    }), 200


@research_bp.route('/documents/<doc_id>/insights', methods=['GET'])
def get_insights(doc_id):
    doc = Document.query.get_or_404(doc_id)
    insights = Insight.query.filter_by(document_id=doc_id).order_by(
        Insight.created_at.desc()
    ).all()
    return jsonify({'insights': [i.to_dict() for i in insights]}), 200


@research_bp.route('/documents/<doc_id>/insights', methods=['POST'])
def generate_insights(doc_id):
    doc = Document.query.get_or_404(doc_id)
    if doc.status != 'ready':
        return jsonify({'error': 'Document is not ready for analysis'}), 400

    api_key = _get_api_key()
    if not api_key:
        return jsonify({'error': 'Gemini API key not configured'}), 503

    data = request.get_json() or {}

    # Get a representative sample of chunks
    chunks = DocumentChunk.query.filter_by(document_id=doc_id).order_by(
        DocumentChunk.chunk_index
    ).limit(25).all()

    text_sample = '\n\n'.join(c.content for c in chunks)

    try:
        model = current_app.config.get('GEMINI_MODEL', 'gemini-3.5-flash')
        from services.gemini_service import generate_insights as gemini_insights
        result = gemini_insights(api_key, model, doc.title, text_sample)
    except Exception as e:
        logger.error(f'Insights generation failed: {e}', exc_info=True)
        return jsonify({'error': f'Insights generation failed: {str(e)[:200]}'}), 500

    insight = Insight(
        document_id=doc_id,
        insight_type='full_analysis',
        content=result.get('raw', ''),
        structured_data=json.dumps(result['structured_data']) if result.get('structured_data') else None,
        source_document_ids=json.dumps([doc_id]),
    )
    db.session.add(insight)
    db.session.commit()

    return jsonify({'insight': insight.to_dict()}), 201


@research_bp.route('/search', methods=['GET'])
def search():
    query_text = request.args.get('q', '').strip()
    document_id = request.args.get('document_id')
    search_type = request.args.get('type', 'semantic')  # keyword, semantic
    top_k = min(int(request.args.get('limit', 10)), 50)

    if not query_text:
        return jsonify({'error': 'Search query is required'}), 400

    if search_type == 'keyword':
        # Simple keyword search in SQLite
        chunk_query = DocumentChunk.query.filter(
            DocumentChunk.content.ilike(f'%{query_text}%')
        )
        if document_id:
            chunk_query = chunk_query.filter_by(document_id=document_id)
        chunks = chunk_query.limit(top_k).all()
        results = [{
            'chunk_id': c.id,
            'document_id': c.document_id,
            'content': c.content,
            'page_number': c.page_number,
            'score': 1.0,
        } for c in chunks]
    else:
        # Semantic search
        embedding_model = current_app.config.get('EMBEDDING_MODEL')
        faiss_folder = current_app.config.get('FAISS_FOLDER', 'storage/faiss_indexes')

        if document_id:
            doc_ids = [document_id]
        else:
            ready_docs = Document.query.filter_by(status='ready').all()
            doc_ids = [d.id for d in ready_docs]

        if not doc_ids:
            return jsonify({'results': [], 'total': 0}), 200

        try:
            from services.embedding_service import embed_query
            from services.vector_store import search_multiple_documents
            query_emb = embed_query(query_text, model_name=embedding_model)
            raw = search_multiple_documents(query_emb, doc_ids, faiss_folder, top_k=top_k)

            results = []
            for r in raw:
                chunk = db.session.get(DocumentChunk, r['chunk_id'])
                if chunk:
                    results.append({
                        'chunk_id': chunk.id,
                        'document_id': chunk.document_id,
                        'content': chunk.content,
                        'page_number': chunk.page_number,
                        'score': r['score'],
                    })
        except Exception as e:
            logger.error(f'Search error: {e}', exc_info=True)
            return jsonify({'error': f'Search failed: {str(e)[:200]}'}), 500

    return jsonify({'results': results, 'total': len(results), 'query': query_text}), 200


@research_bp.route('/stats', methods=['GET'])
def get_stats():
    """Return application statistics."""
    from models.models import Conversation, Note, Collection
    from sqlalchemy import func

    total_docs = Document.query.count()
    ready_docs = Document.query.filter_by(status='ready').count()
    total_chunks = DocumentChunk.query.count()
    total_conversations = Conversation.query.count()
    total_notes = Note.query.count()
    total_collections = Collection.query.count()

    return jsonify({
        'total_documents': total_docs,
        'ready_documents': ready_docs,
        'total_chunks': total_chunks,
        'total_conversations': total_conversations,
        'total_notes': total_notes,
        'total_collections': total_collections,
    }), 200

