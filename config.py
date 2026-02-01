import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

def _resolve_sqlite_path(uri: str, project_root: str) -> str:
    """Convert relative SQLite URI to absolute path.
    
    Args:
        uri: SQLite URI like 'sqlite:///instance/local.db'
        project_root: Absolute path to project root directory
        
    Returns:
        Absolute SQLite URI like 'sqlite:///E:/path/to/project/instance/local.db'
    """
    if not uri.startswith('sqlite:///'):
        return uri
    
    # Extract path after sqlite:///
    relative_path = uri[10:]  # Remove 'sqlite:///'
    
    # Join with project root and normalize path
    absolute_path = os.path.abspath(os.path.join(project_root, relative_path))
    
    # Ensure instance directory exists BEFORE any SQLAlchemy connection attempt
    instance_dir = os.path.dirname(absolute_path)
    if instance_dir and not os.path.exists(instance_dir):
        os.makedirs(instance_dir, exist_ok=True)
    
    # Normalize separators for Windows (SQLite expects forward slashes)
    # On Windows, SQLite URI format is: sqlite:///E:/path/to/db.db (no leading slash before drive)
    absolute_path = absolute_path.replace('\\', '/')
    
    # DO NOT add leading slash before Windows drive letter
    # SQLite handles E:/ directly, not /E:/
    
    return f'sqlite:///{absolute_path}'
            
class Config:
    default_admins = {"admin"}  # fallback
    env_admins = {u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()}
    ADMIN_USERNAMES = default_admins | env_admins

    # Compute IS_DEV once
    _env = os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "production"
    IS_DEV = str(_env).lower() in {"development", "dev"}

    # In production SECRET_KEY must be set.
    # In development we allow a fallback to avoid breaking local runs.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY and IS_DEV:
        SECRET_KEY = "dev-secret-key"
    
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:////app/instance/local.db'
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_CREATE_DB = os.environ.get("AUTO_CREATE_DB", "0") == "1"