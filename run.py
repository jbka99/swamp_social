import os
from app import create_app, db
from app.models import User, Thread
import cloudinary

debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']

app = create_app()

def init_cloudinary():
    cloudinary.config(
        cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
        api_key=os.getenv('CLOUDINARY_API_KEY'),
        api_secret=os.getenv('CLOUDINARY_API_SECRET'),
        secure=True,
    )

def ensure_tables():
    with app.app_context():
        db.create_all()

ensure_tables()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Thread': Thread, 'Post': Thread}  # Post alias for compatibility

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)