"""Notes and Collections routes."""
import json
import logging
from flask import Blueprint, request, jsonify
from extensions import db
from models.models import Note, Collection, CollectionDocument, Document

logger = logging.getLogger(__name__)
notes_bp = Blueprint('notes', __name__)
collections_bp = Blueprint('collections', __name__)


# ─── Notes ────────────────────────────────────────────────────────────────────

@notes_bp.route('', methods=['GET'])
def list_notes():
    doc_id = request.args.get('document_id')
    query = Note.query
    if doc_id:
        query = query.filter_by(document_id=doc_id)
    notes = query.order_by(Note.updated_at.desc()).all()
    return jsonify({'notes': [n.to_dict() for n in notes]}), 200


@notes_bp.route('', methods=['POST'])
def create_note():
    data = request.get_json() or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({'error': 'Note content is required'}), 400

    note = Note(
        document_id=data.get('document_id'),
        page_number=data.get('page_number'),
        title=data.get('title', '')[:500] or None,
        content=content,
        tags=json.dumps(data.get('tags', [])),
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'note': note.to_dict()}), 201


@notes_bp.route('/<note_id>', methods=['PATCH'])
def update_note(note_id):
    note = Note.query.get_or_404(note_id)
    data = request.get_json() or {}

    if 'content' in data:
        note.content = data['content']
    if 'title' in data:
        note.title = data['title'][:500] if data['title'] else None
    if 'tags' in data:
        note.tags = json.dumps(data['tags'])
    if 'page_number' in data:
        note.page_number = data['page_number']

    db.session.commit()
    return jsonify({'note': note.to_dict()}), 200


@notes_bp.route('/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'}), 200


@notes_bp.route('/<note_id>/export', methods=['GET'])
def export_note(note_id):
    from flask import Response
    note = Note.query.get_or_404(note_id)
    md = f'# {note.title or "Note"}\n\n{note.content}\n'
    return Response(
        md,
        mimetype='text/markdown',
        headers={'Content-Disposition': f'attachment; filename="note-{note_id[:8]}.md"'},
    )


# ─── Collections ──────────────────────────────────────────────────────────────

@collections_bp.route('', methods=['GET'])
def list_collections():
    colls = Collection.query.order_by(Collection.updated_at.desc()).all()
    return jsonify({'collections': [c.to_dict() for c in colls]}), 200


@collections_bp.route('', methods=['POST'])
def create_collection():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Collection name is required'}), 400

    coll = Collection(name=name[:300], description=data.get('description', ''))
    db.session.add(coll)
    db.session.commit()
    return jsonify({'collection': coll.to_dict()}), 201


@collections_bp.route('/<coll_id>', methods=['GET'])
def get_collection(coll_id):
    coll = Collection.query.get_or_404(coll_id)
    return jsonify({'collection': coll.to_dict(include_documents=True)}), 200


@collections_bp.route('/<coll_id>', methods=['PATCH'])
def update_collection(coll_id):
    coll = Collection.query.get_or_404(coll_id)
    data = request.get_json() or {}
    if 'name' in data:
        coll.name = data['name'][:300]
    if 'description' in data:
        coll.description = data['description']
    db.session.commit()
    return jsonify({'collection': coll.to_dict()}), 200


@collections_bp.route('/<coll_id>', methods=['DELETE'])
def delete_collection(coll_id):
    coll = Collection.query.get_or_404(coll_id)
    db.session.delete(coll)
    db.session.commit()
    return jsonify({'message': 'Collection deleted'}), 200


@collections_bp.route('/<coll_id>/documents', methods=['POST'])
def add_document_to_collection(coll_id):
    coll = Collection.query.get_or_404(coll_id)
    data = request.get_json() or {}
    doc_id = data.get('document_id')
    if not doc_id:
        return jsonify({'error': 'document_id is required'}), 400

    doc = Document.query.get_or_404(doc_id)

    # Check if already in collection
    existing = CollectionDocument.query.filter_by(
        collection_id=coll_id, document_id=doc_id
    ).first()
    if existing:
        return jsonify({'error': 'Document already in collection'}), 409

    cd = CollectionDocument(collection_id=coll_id, document_id=doc_id)
    db.session.add(cd)
    db.session.commit()
    return jsonify({'message': 'Document added to collection', 'collection': coll.to_dict(include_documents=True)}), 200


@collections_bp.route('/<coll_id>/documents/<doc_id>', methods=['DELETE'])
def remove_document_from_collection(coll_id, doc_id):
    cd = CollectionDocument.query.filter_by(
        collection_id=coll_id, document_id=doc_id
    ).first_or_404()
    db.session.delete(cd)
    db.session.commit()
    return jsonify({'message': 'Document removed from collection'}), 200

