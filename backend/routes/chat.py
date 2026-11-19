"""Chat and conversation routes."""
import json
import logging
from flask import Blueprint, request, jsonify, current_app
from extensions import db
from models.models import Conversation, Message, Document

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/conversations', methods=['POST'])
def create_conversation():
    data = request.get_json() or {}
    doc_ids = data.get('document_ids', [])

    conv = Conversation(
        title=data.get('title', 'New Conversation'),
        document_ids=json.dumps(doc_ids),
    )
    db.session.add(conv)
    db.session.commit()
    return jsonify({'conversation': conv.to_dict()}), 201


@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    search = request.args.get('search', '').strip()
    query = Conversation.query
    if search:
        query = query.filter(Conversation.title.ilike(f'%{search}%'))
    convs = query.order_by(Conversation.updated_at.desc()).all()
    return jsonify({'conversations': [c.to_dict() for c in convs]}), 200


@chat_bp.route('/conversations/<conv_id>', methods=['GET'])
def get_conversation(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    return jsonify({'conversation': conv.to_dict(include_messages=True)}), 200


@chat_bp.route('/conversations/<conv_id>', methods=['PATCH'])
def update_conversation(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    data = request.get_json() or {}

    if 'title' in data:
        conv.title = data['title'][:500]
    if 'document_ids' in data:
        conv.document_ids = json.dumps(data['document_ids'])

    db.session.commit()
    return jsonify({'conversation': conv.to_dict()}), 200


@chat_bp.route('/conversations/<conv_id>', methods=['DELETE'])
def delete_conversation(conv_id):
    conv = Conversation.query.get_or_404(conv_id)
    db.session.delete(conv)
    db.session.commit()
    return jsonify({'message': 'Conversation deleted'}), 200


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """Main RAG chat endpoint."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    question = (data.get('question') or data.get('message', '')).strip()
    if not question:
        return jsonify({'error': 'Question is required'}), 400

    document_ids = data.get('document_ids', [])
    conversation_id = data.get('conversation_id')

    if not document_ids:
        return jsonify({'error': 'At least one document must be selected'}), 400

    # Validate documents exist and are ready
    docs = Document.query.filter(
        Document.id.in_(document_ids),
        Document.status == 'ready',
    ).all()

    if not docs:
        return jsonify({'error': 'No ready documents found. Please wait for processing to complete.'}), 400

    ready_ids = [d.id for d in docs]

    # Check Gemini configuration
    api_key = current_app.config.get('GEMINI_API_KEY', '')
    if not api_key or api_key == 'your_gemini_api_key_here':
        return jsonify({'error': 'Gemini API key not configured. Please add it to backend/.env'}), 503

    model = current_app.config.get('GEMINI_MODEL', 'gemini-3.5-flash')
    embedding_model = current_app.config.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    faiss_folder = current_app.config.get('FAISS_FOLDER', 'storage/faiss_indexes')
    top_k = current_app.config.get('TOP_K_RETRIEVAL', 5)

    # Get or create conversation
    conv = None
    if conversation_id:
        conv = db.session.get(Conversation, conversation_id)

    if not conv:
        doc_titles = ', '.join(d.title[:30] for d in docs[:2])
        conv = Conversation(
            title=question[:80] if len(question) < 80 else question[:77] + '...',
            document_ids=json.dumps(ready_ids),
        )
        db.session.add(conv)
        db.session.flush()

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role='user',
        content=question,
    )
    db.session.add(user_msg)
    db.session.flush()

    # Get conversation history
    history = []
    if conv:
        recent_msgs = Message.query.filter_by(conversation_id=conv.id).order_by(
            Message.created_at.desc()
        ).limit(10).all()
        history = [{'role': m.role, 'content': m.content} for m in reversed(recent_msgs)]

    # Retrieve relevant chunks
    try:
        from services.rag_service import retrieve_relevant_chunks
        relevant_chunks = retrieve_relevant_chunks(
            question=question,
            document_ids=ready_ids,
            db_session=db.session,
            embedding_model=embedding_model,
            faiss_folder=faiss_folder,
            top_k=top_k,
        )
    except Exception as e:
        logger.error(f'Retrieval error: {e}', exc_info=True)
        return jsonify({'error': f'Retrieval failed: {str(e)}'}), 500

    # Generate answer
    try:
        from services.gemini_service import generate_rag_answer
        result = generate_rag_answer(
            api_key=api_key,
            model=model,
            question=question,
            context_chunks=relevant_chunks,
            conversation_history=history,
            document_title=docs[0].title if docs else '',
        )
    except Exception as e:
        logger.error(f'Gemini error: {e}', exc_info=True)
        err_str = str(e)
        if 'API_KEY' in err_str or 'PERMISSION' in err_str.upper():
            return jsonify({'error': 'Invalid Gemini API key. Check your backend/.env configuration.'}), 401
        if 'QUOTA' in err_str.upper() or 'RESOURCE_EXHAUSTED' in err_str.upper():
            return jsonify({'error': 'Gemini API quota exceeded. Please try again later.'}), 429
        return jsonify({'error': f'AI generation failed: {err_str[:200]}'}), 500

    # Build citations list
    citations = []
    for chunk in result.get('raw_citations', []):
        citations.append({
            'chunk_id': chunk.get('chunk_id'),
            'document_id': chunk.get('document_id'),
            'document_title': chunk.get('document_title', ''),
            'page_number': chunk.get('page_number'),
            'excerpt': chunk.get('content', '')[:300],
            'score': chunk.get('score', 0),
        })

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conv.id,
        role='assistant',
        content=result['answer'],
        citations=json.dumps(citations),
        follow_up_questions=json.dumps(result.get('suggested_questions', [])),
    )
    db.session.add(assistant_msg)

    conv.document_ids = json.dumps(ready_ids)
    db.session.commit()

    return jsonify({
        'conversation_id': conv.id,
        'message': assistant_msg.to_dict(),
        'citations': citations,
        'suggested_questions': result.get('suggested_questions', []),
    }), 200


@chat_bp.route('/messages/<msg_id>/feedback', methods=['POST'])
def message_feedback(msg_id):
    msg = Message.query.get_or_404(msg_id)
    data = request.get_json() or {}
    feedback = data.get('feedback')
    if feedback not in ('helpful', 'not_helpful'):
        return jsonify({'error': 'Invalid feedback value'}), 400
    msg.feedback = feedback
    db.session.commit()
    return jsonify({'message': 'Feedback recorded'}), 200

