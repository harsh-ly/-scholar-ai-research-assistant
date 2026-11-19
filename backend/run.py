"""Entry point for Scholar AI Flask server."""
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '1') == '1'
    host = os.environ.get('FLASK_HOST', '0.0.0.0')

    print('\n' + '=' * 60)
    print('  [Scholar AI] Research Paper Assistant')
    print('=' * 60)
    print(f'  Application URL : http://127.0.0.1:{port}')
    print(f'  API Health      : http://127.0.0.1:{port}/api/v1/health')
    print(f'  Debug mode      : {debug}')
    print('=' * 60 + '\n')

    app.run(host=host, port=port, debug=debug, use_reloader=False)
