from flask import Blueprint

bp = Blueprint('routes', __name__)

# Важно: импорты в конце, чтобы bp уже существовал
from app.routes import auth, posts, users  # noqa: E402,F401