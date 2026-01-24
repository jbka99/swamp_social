import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
            
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
    
    uri = os.environ.get('DATABASE_URL')
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    
    if not uri and IS_DEV:
        # safe local default
        uri = "sqlite:///instance/local.db"

    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Enable only for local/dev if you really want auto-create (migrations still recommended)
    AUTO_CREATE_DB = os.environ.get("AUTO_CREATE_DB", "0") in {"1", "true", "True"}