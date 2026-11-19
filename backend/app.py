"""Flask application factory for Scholar AI."""
import os
import logging
from flask import Flask, jsonify
from config import get_config


def create_app(config_class=None):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    frontend_dir = os.path.join(base_dir, 'frontend')

    app = Flask(
        __name__,
        instance_relative_config=False,
        static_folder=frontend_dir,
        static_url_path='',
    )

    # Load configuration
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Ensure storage directories exist
    for folder in [
        app.config.get('UPLOAD_FOLDER', 'storage/uploads'),
        app.config.get('FAISS_FOLDER', 'storage/faiss_indexes'),
    ]:
        os.makedirs(folder, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    # Initialize extensions
    from extensions import db, cors
    db.init_app(app)
    cors.init_app(app, resources={
        r'/api/*': {
            'origins': app.config.get('CORS_ORIGINS', ['*']),
            'methods': ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
            'allow_headers': ['Content-Type', 'Authorization'],
        }
    })

    # Register blueprints
    from routes.health import health_bp
    from routes.documents import documents_bp
    from routes.chat import chat_bp
    from routes.research import research_bp
    from routes.notes import notes_bp, collections_bp
    from routes.exports import exports_bp

    prefix = '/api/v1'
    app.register_blueprint(health_bp, url_prefix=prefix)
    app.register_blueprint(documents_bp, url_prefix=f'{prefix}/documents')
    app.register_blueprint(chat_bp, url_prefix=prefix)
    app.register_blueprint(research_bp, url_prefix=prefix)
    app.register_blueprint(notes_bp, url_prefix=f'{prefix}/notes')
    app.register_blueprint(collections_bp, url_prefix=f'{prefix}/collections')
    app.register_blueprint(exports_bp, url_prefix=f'{prefix}/exports')

    # Serve index.html at root
    @app.route('/')
    def serve_index():
        return app.send_static_file('index.html')

    # Initialize database tables
    with app.app_context():
        from database import init_db
        init_db(app)

    # Global error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'Bad request', 'detail': str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({'error': 'File too large. Maximum size is 50MB'}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    return app
