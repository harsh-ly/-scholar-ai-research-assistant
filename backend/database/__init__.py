"""Database initialization and utilities."""
import os
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

        # Ensure storage directories exist
        upload_folder = app.config.get('UPLOAD_FOLDER', 'storage/uploads')
        faiss_folder = app.config.get('FAISS_FOLDER', 'storage/faiss_indexes')
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(faiss_folder, exist_ok=True)

