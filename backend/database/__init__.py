"""Database initialization and utilities."""
from extensions import db


def init_db(app):
    """Initialize the database."""
    with app.app_context():
        # Import all models so SQLAlchemy knows about them
        from models.models import (
            Document, DocumentChunk, Conversation, Message,
            Summary, Note, Collection, CollectionDocument,
            Insight, ProcessingJob
        )
        db.create_all()

