"""Export routes."""
import json
import logging
from flask import Blueprint, request, jsonify, Response, current_app
from extensions import db
from models.models import Document, DocumentChunk, Summary, Note, Conversation, Message

logger = logging.getLogger(__name__)
exports_bp = Blueprint('exports', __name__)


def _safe_filename(name: str) -> str:
    import re
    name = re.sub(r'[^\w\s\-.]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    return name[:100] or 'export'


@exports_bp.route('', methods=['POST'])
def create_export():
    data = request.get_json() or {}
    export_type = data.get('type', 'summary')
    resource_id = data.get('resource_id', '')
    format_type = data.get('format', 'markdown')

    if export_type == 'summary':
        summary = Summary.query.get_or_404(resource_id)
        doc = db.session.get(Document, summary.document_id)
        title = doc.title if doc else 'Document'
        content = _build_summary_md(summary, title)
        filename = _safe_filename(f'summary-{title}') + '.md'
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    elif export_type == 'notes':
        doc_id = data.get('document_id')
        notes = Note.query.filter_by(document_id=doc_id).all() if doc_id else Note.query.all()
        content = _build_notes_md(notes)
        filename = 'research-notes.md'
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    elif export_type == 'conversation':
        conv = Conversation.query.get_or_404(resource_id)
        msgs = Message.query.filter_by(conversation_id=conv.id).order_by(Message.created_at).all()
        content = _build_conversation_md(conv, msgs)
        filename = _safe_filename(f'conversation-{conv.title}') + '.md'
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    elif export_type == 'comparison':
        structured = data.get('comparison_data', {})
        doc_titles = data.get('document_titles', [])
        content = _build_comparison_md(structured, doc_titles)
        filename = 'paper-comparison.md'
        return Response(content, mimetype='text/markdown',
                        headers={'Content-Disposition': f'attachment; filename="{filename}"'})

    return jsonify({'error': 'Unknown export type'}), 400


def _build_summary_md(summary, title: str) -> str:
    lines = [f'# Summary: {title}\n', f'**Type:** {summary.summary_type}\n',
             f'**Generated:** {summary.created_at}\n\n---\n']
    if summary.structured_data:
        try:
            sd = json.loads(summary.structured_data)
            for key, val in sd.items():
                if val:
                    lines.append(f'\n## {key.replace("_", " ").title()}\n\n{val}\n')
        except Exception:
            lines.append(summary.content)
    else:
        lines.append(summary.content)
    return '\n'.join(lines)


def _build_notes_md(notes) -> str:
    lines = ['# Research Notes\n']
    for note in notes:
        lines.append(f'\n## {note.title or "Note"}\n')
        if note.page_number:
            lines.append(f'*Page {note.page_number}*\n')
        lines.append(f'\n{note.content}\n')
        lines.append('\n---\n')
    return '\n'.join(lines)


def _build_conversation_md(conv, messages) -> str:
    lines = [f'# Conversation: {conv.title}\n\n---\n']
    for msg in messages:
        role = '**You**' if msg.role == 'user' else '**Scholar AI**'
        lines.append(f'\n{role}\n\n{msg.content}\n')
    return '\n'.join(lines)


def _build_comparison_md(data: dict, titles: list) -> str:
    lines = ['# Paper Comparison\n']
    if titles:
        lines.append('**Papers Compared:**\n')
        for i, t in enumerate(titles, 1):
            lines.append(f'{i}. {t}')
    lines.append('\n---\n')
    if isinstance(data, dict):
        for key, val in data.items():
            lines.append(f'\n## {key.replace("_", " ").title()}\n')
            if isinstance(val, dict):
                for k2, v2 in val.items():
                    lines.append(f'\n### {k2.title()}\n{v2}\n')
            elif isinstance(val, list):
                for item in val:
                    lines.append(f'- {item}')
            else:
                lines.append(str(val))
    return '\n'.join(lines)

