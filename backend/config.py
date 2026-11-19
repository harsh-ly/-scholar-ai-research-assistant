import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///scholar_ai.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
    }

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _upload = os.environ.get('UPLOAD_FOLDER', 'storage/uploads')
    UPLOAD_FOLDER = _upload if os.path.isabs(_upload) else os.path.normpath(os.path.join(BASE_DIR, _upload))
    _faiss = os.environ.get('FAISS_FOLDER', 'storage/faiss_indexes')
    FAISS_FOLDER = _faiss if os.path.isabs(_faiss) else os.path.normpath(os.path.join(BASE_DIR, _faiss))
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 52428800))  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}

    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash')

    EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')
    CHUNK_SIZE = int(os.environ.get('CHUNK_SIZE', 1000))
    CHUNK_OVERLAP = int(os.environ.get('CHUNK_OVERLAP', 200))
    TOP_K_RETRIEVAL = int(os.environ.get('TOP_K_RETRIEVAL', 5))

    CORS_ORIGINS = os.environ.get(
        'CORS_ORIGINS',
        'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500,http://localhost:5000,http://127.0.0.1:5000'
    ).split(',')

    RATE_LIMIT_CHAT = 20
    REQUEST_TIMEOUT = 120
    MAX_RETRIES = 3


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    GEMINI_API_KEY = 'test-key-do-not-use'
    UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'scholar_ai_test_uploads')
    FAISS_FOLDER = os.path.join(tempfile.gettempdir(), 'scholar_ai_test_faiss')
    # Use in-memory DB for tests — no thread restriction needed
    SQLALCHEMY_ENGINE_OPTIONS = {}


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config():
    env = os.environ.get('FLASK_ENV', 'development')
    return config_map.get(env, DevelopmentConfig)
