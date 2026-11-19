"""Health check routes."""
import os
from flask import Blueprint, jsonify, current_app
from sqlalchemy import text as sql_text
from extensions import db

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'Scholar AI'}), 200


@health_bp.route('/health/ready')
def ready():
    checks = {}

    # DB check
    try:
        db.session.execute(sql_text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'

    # Gemini key check
    api_key = current_app.config.get('GEMINI_API_KEY', '')
    checks['gemini_configured'] = bool(api_key and api_key != 'your_gemini_api_key_here')

    # Embedding model check
    checks['embedding_model'] = current_app.config.get('EMBEDDING_MODEL')

    # Storage check
    upload_folder = current_app.config.get('UPLOAD_FOLDER')
    checks['upload_storage'] = 'ok' if os.path.isdir(upload_folder) else 'missing'

    all_ok = checks['database'] == 'ok' and checks['upload_storage'] == 'ok'
    return jsonify({'status': 'ready' if all_ok else 'degraded', 'checks': checks}), 200 if all_ok else 503

