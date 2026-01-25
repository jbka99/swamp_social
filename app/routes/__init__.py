from flask import Blueprint
import re
from markupsafe import Markup

bp = Blueprint('routes', __name__)

@bp.app_template_filter('mentions_to_links')
def mentions_to_links_filter(text):
    """Convert @username mentions to clickable links"""
    if not text:
        return ''
    
    from markupsafe import escape, Markup
    
    # Pattern: @username (alphanumeric and underscore, 1-64 chars)
    pattern = r'@([a-zA-Z0-9_]{1,64})'
    
    # Split text into parts: before mention, mention, after mention
    parts = []
    last_end = 0
    
    for match in re.finditer(pattern, text):
        # Add text before mention (escaped)
        if match.start() > last_end:
            parts.append(escape(text[last_end:match.start()]))
        
        # Add mention as link (username is already validated by regex)
        username = match.group(1)
        url = f'/user/{username}'
        parts.append(f'<a href="{url}" class="mention">@{escape(username)}</a>')
        
        last_end = match.end()
    
    # Add remaining text (escaped)
    if last_end < len(text):
        parts.append(escape(text[last_end:]))
    
    return Markup(''.join(parts))

# Важно: импорты в конце, чтобы bp уже существовал
from app.routes import auth, posts, users, admin  # noqa: E402,F401