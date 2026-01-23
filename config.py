import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))
            
class Config:
    default_admins = {"admin"}  # fallback
    env_admins = {u.strip() for u in os.getenv("ADMIN_USERNAMES", "").split(",") if u.strip()}
    ADMIN_USERNAMES = default_admins | env_admins

    # In production SECRET_KEY must be set.
    # In development we allow a fallback to avoid breaking local runs.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        env = os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "production"
        if str(env).lower() in {"development", "dev"}:
            SECRET_KEY = "dev-secret-key"
        else:
            raise RuntimeError("SECRET_KEY is not set")
    
    uri = os.environ.get('DATABASE_URL')
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    
    if not uri:
        env = os.environ.get("FLASK_ENV") or os.environ.get("ENV") or "production"
        if str(env).lower() in {"development", "dev"}:
            # safe local default
            uri = "sqlite:///instance/local.db"
        else:
            raise RuntimeError("DATABASE_URL is not set")

    SQLALCHEMY_DATABASE_URI = uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Enable only for local/dev if you really want auto-create (migrations still recommended)
    AUTO_CREATE_DB = os.environ.get("AUTO_CREATE_DB", "0") in {"1", "true", "True"}