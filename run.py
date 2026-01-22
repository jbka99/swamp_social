import os
from app import create_app, db
from app.models import User, Post

debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)