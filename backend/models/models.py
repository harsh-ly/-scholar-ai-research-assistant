"""Database models for Scholar AI."""
import uuid
from datetime import datetime, timezone
from extensions import db


def gen_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class Document(db.Model):
    __tablename__ = 'documents'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title = db.Column(db.String(500), nullable=False)
    filename = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(500), nullable=False)
    file_hash = db.Column(db.String(64), unique=True, nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    file_path = db.Column(db.String(1000), nullable=False)

    # Metadata
    authors = db.Column(db.Text, nullable=True)
    publication_year = db.Column(db.Integer, nullable=True)
    research_area = db.Column(db.String(300), nullable=True)
    document_type = db.Column(db.String(100), nullable=True)
    total_pages = db.Column(db.Integer, nullable=True)
    abstract = db.Column(db.Text, nullable=True)
    is_scanned = db.Column(db.Boolean, default=False)

    # Processing
    status = db.Column(db.String(50), default='uploaded')  # uploaded, processing, ready, failed
    error_message = db.Column(db.Text, nullable=True)
    processing_started_at = db.Column(db.DateTime, nullable=True)
    processing_completed_at = db.Column(db.DateTime, nullable=True)
    embedding_model = db.Column(db.String(200), nullable=True)
    chunk_count = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    chunks = db.relationship('DocumentChunk', back_populates='document',
                              cascade='all, delete-orphan', lazy='dynamic')
    summaries = db.relationship('Summary', back_populates='document',
                                 cascade='all, delete-orphan', lazy='dynamic')
    notes = db.relationship('Note', back_populates='document',
                             cascade='all, delete-orphan', lazy='dynamic')
    insights = db.relationship('Insight', back_populates='document',
                                cascade='all, delete-orphan', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_document_status', 'status'),
        db.Index('idx_document_created', 'created_at'),
        db.Index('idx_document_hash', 'file_hash'),
    )

    def to_dict(self, include_chunks=False):
        d = {
            'id': self.id,
            'title': self.title,
            'filename': self.original_filename,
            'authors': self.authors,
            'publication_year': self.publication_year,
            'research_area': self.research_area,
            'document_type': self.document_type,
            'total_pages': self.total_pages,
            'abstract': self.abstract,
            'is_scanned': self.is_scanned,
            'status': self.status,
            'error_message': self.error_message,
            'chunk_count': self.chunk_count,
            'embedding_model': self.embedding_model,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'processing_completed_at': self.processing_completed_at.isoformat()
                if self.processing_completed_at else None,
        }
        return d


class DocumentChunk(db.Model):
    __tablename__ = 'document_chunks'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, nullable=True)
    page_range_start = db.Column(db.Integer, nullable=True)
    page_range_end = db.Column(db.Integer, nullable=True)
    char_start = db.Column(db.Integer, nullable=True)
    char_end = db.Column(db.Integer, nullable=True)
    faiss_index_id = db.Column(db.Integer, nullable=True)
    token_count = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    document = db.relationship('Document', back_populates='chunks')

    __table_args__ = (
        db.Index('idx_chunk_document', 'document_id'),
        db.Index('idx_chunk_page', 'document_id', 'page_number'),
        db.Index('idx_chunk_faiss', 'faiss_index_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'chunk_index': self.chunk_index,
            'content': self.content,
            'page_number': self.page_number,
            'page_range_start': self.page_range_start,
            'page_range_end': self.page_range_end,
            'faiss_index_id': self.faiss_index_id,
        }


class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title = db.Column(db.String(500), default='New Conversation')
    document_ids = db.Column(db.Text, nullable=True)  # JSON list of document IDs
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    messages = db.relationship('Message', back_populates='conversation',
                                cascade='all, delete-orphan',
                                order_by='Message.created_at', lazy='dynamic')

    __table_args__ = (
        db.Index('idx_conversation_updated', 'updated_at'),
    )

    def to_dict(self, include_messages=False):
        import json
        d = {
            'id': self.id,
            'title': self.title,
            'document_ids': json.loads(self.document_ids) if self.document_ids else [],
            'message_count': self.messages.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            d['messages'] = [m.to_dict() for m in self.messages]
        return d


class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    conversation_id = db.Column(db.String(36),
                                 db.ForeignKey('conversations.id', ondelete='CASCADE'),
                                 nullable=False)
    role = db.Column(db.String(20), nullable=False)  # user, assistant, system
    content = db.Column(db.Text, nullable=False)
    citations = db.Column(db.Text, nullable=True)    # JSON list of citation objects
    follow_up_questions = db.Column(db.Text, nullable=True)  # JSON list
    feedback = db.Column(db.String(20), nullable=True)  # helpful, not_helpful
    created_at = db.Column(db.DateTime, default=utc_now)

    conversation = db.relationship('Conversation', back_populates='messages')

    __table_args__ = (
        db.Index('idx_message_conversation', 'conversation_id'),
        db.Index('idx_message_created', 'created_at'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'citations': json.loads(self.citations) if self.citations else [],
            'follow_up_questions': json.loads(self.follow_up_questions)
                if self.follow_up_questions else [],
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Summary(db.Model):
    __tablename__ = 'summaries'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=False)
    summary_type = db.Column(db.String(50), default='detailed')  # short, detailed, section_wise
    content = db.Column(db.Text, nullable=False)
    structured_data = db.Column(db.Text, nullable=True)  # JSON with sections
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    document = db.relationship('Document', back_populates='summaries')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'document_id': self.document_id,
            'summary_type': self.summary_type,
            'content': self.content,
            'structured_data': json.loads(self.structured_data) if self.structured_data else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=True)
    page_number = db.Column(db.Integer, nullable=True)
    title = db.Column(db.String(500), nullable=True)
    content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.Text, nullable=True)  # JSON list
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    document = db.relationship('Document', back_populates='notes')

    __table_args__ = (
        db.Index('idx_note_document', 'document_id'),
    )

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'document_id': self.document_id,
            'page_number': self.page_number,
            'title': self.title,
            'content': self.content,
            'tags': json.loads(self.tags) if self.tags else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Collection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    collection_documents = db.relationship('CollectionDocument',
                                            back_populates='collection',
                                            cascade='all, delete-orphan')

    def to_dict(self, include_documents=False):
        d = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'document_count': len(self.collection_documents),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_documents:
            d['documents'] = [cd.document.to_dict() for cd in self.collection_documents
                               if cd.document]
        return d


class CollectionDocument(db.Model):
    __tablename__ = 'collection_documents'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    collection_id = db.Column(db.String(36),
                               db.ForeignKey('collections.id', ondelete='CASCADE'),
                               nullable=False)
    document_id = db.Column(db.String(36),
                             db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=False)
    added_at = db.Column(db.DateTime, default=utc_now)

    collection = db.relationship('Collection', back_populates='collection_documents')
    document = db.relationship('Document')

    __table_args__ = (
        db.UniqueConstraint('collection_id', 'document_id', name='uq_collection_document'),
    )


class Insight(db.Model):
    __tablename__ = 'insights'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=True)
    insight_type = db.Column(db.String(100), nullable=False)  # themes, concepts, gaps, etc.
    content = db.Column(db.Text, nullable=False)
    structured_data = db.Column(db.Text, nullable=True)  # JSON
    source_document_ids = db.Column(db.Text, nullable=True)  # JSON list
    created_at = db.Column(db.DateTime, default=utc_now)

    document = db.relationship('Document', back_populates='insights')

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'document_id': self.document_id,
            'insight_type': self.insight_type,
            'content': self.content,
            'structured_data': json.loads(self.structured_data) if self.structured_data else None,
            'source_document_ids': json.loads(self.source_document_ids)
                if self.source_document_ids else [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ProcessingJob(db.Model):
    __tablename__ = 'processing_jobs'

    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id', ondelete='CASCADE'),
                             nullable=False)
    job_type = db.Column(db.String(50), default='full_processing')
    status = db.Column(db.String(50), default='pending')  # pending, running, done, failed
    progress = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

