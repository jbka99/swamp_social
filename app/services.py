from dataclasses import dataclass
from app.extensions import db
from app.models import Post
from typing import Optional

def get_main_feed(page: int = 1, per_page: int = 20):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)
    query = Post.query.order_by(Post.date_posted.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)

@dataclass(frozen=True)
class DeletePostResult:
    deleted: bool
    reason: str  # "ok" | "not_found" | "forbidden"


# Удаляем пост, если он существует и у пользователя есть права

def delete_post(post_id: int, actor_user_id: int, actor_is_admin: bool) -> DeletePostResult:

    post = db.session.get(Post, int(post_id))
    if post is None:
        return DeletePostResult(deleted=False, reason="not_found")

    can_delete = actor_is_admin or (post.user_id == actor_user_id)
    if not can_delete:
        return DeletePostResult(deleted=False, reason="forbidden")

    db.session.delete(post)
    db.session.commit()
    return DeletePostResult(deleted=True, reason="ok")

@dataclass(frozen=True)
class CreatePostResult:
    created: bool
    post_id: Optional[int]
    reason: str  # "ok" | "empty_content"

def create_post(user_id: int, title: str, content: str) -> CreatePostResult:

    content = (content or "").strip()
    title = (title or "").strip()

    if not content:
        return CreatePostResult(created=False, post_id=None, reason="empty_content")

    # Если title пустой, чтобы не падало заглушка
    if not title:
        title = "Без названия"

    post = Post(title=title, content=content, user_id=user_id)
    db.session.add(post)
    db.session.commit()

    return CreatePostResult(created=True, post_id=post.id, reason="ok")