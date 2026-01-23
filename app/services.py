from dataclasses import dataclass
from app.extensions import db
from app.models import Post, User
from typing import Optional, Iterable
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from flask import current_app

# Admin op

def ensure_admin_flag(user: User) -> bool:
    admins = current_app.config.get("ADMIN_USERNAMES", set())
    if user and user.username in admins and not user.is_admin:
        user.is_admin = True
        db.session.commit()
        return True
    return False

@dataclass
class DeleteAllPostsFromUserResult:
    deleted: bool
    deleted_count: int
    reason: str # "ok" | "not_found" | "forbidden"

def admin_delete_all_posts_from_user(target_user_id: int, actor_is_admin: bool) -> DeleteAllPostsFromUserResult:
    if not actor_is_admin:
        return DeleteAllPostsFromUserResult(deleted=False, deleted_count=0, reason="forbidden")
    
    user = db.session.get(User, int(target_user_id))
    if user is None:
        return DeleteAllPostsFromUserResult(deleted=False, deleted_count=0, reason="not_found")
    
    deleted_count = (
        Post.query
        .filter(Post.user_id == user.id)
        .delete(synchronize_session=False)
    )
    db.session.commit()
    return DeleteAllPostsFromUserResult(deleted=True, deleted_count=int(deleted_count), reason="ok")

@dataclass(frozen=True)
class DeleteUserResult:
    deleted: bool
    reason: str # "ok" | "not_found" | "forbidden" | "self_deleted_blocked"

def admin_delete_user(target_user_id: int, actor_user_id: int, actor_is_admin: bool) -> DeleteUserResult:
    if not actor_is_admin:
        return DeleteUserResult(deleted=False, reason="forbidden")
    
    if int(target_user_id) == int(actor_user_id):
        return DeleteUserResult(deleted=False, reason="self_delete_blocked")
    
    user = db.session.get(User, int(target_user_id))
    if user is None:
        return DeleteUserResult(deleted=False, reason="not_found")
    
    # Сначала удаляю посты, а потом пользователя
    Post.query.filter(Post.user_id == user.id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()

    return DeleteUserResult(deleted=True, reason="ok")

@dataclass(frozen=True)
class BulkDeleteUsersResult:
    deleted: bool
    deleted_count: int
    reason: str # "ok" | "forbidden" | "empty"

def admin_bulk_delete_users(
        target_user_ids: Iterable[int],
        actor_user_id: int,
        actor_is_admin: bool,
) -> BulkDeleteUsersResult:
    if not actor_is_admin:
        return BulkDeleteUsersResult(deleted=False, deleted_count=0, reason="forbidden")

    ids = []
    for x in target_user_ids:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue

    ids = [x for x in ids if x != int(actor_user_id)]

    if not ids:
        return BulkDeleteUsersResult(deleted=False, deleted_count=0, reason="empty")
    
    Post.query.filter(Post.user_id.in_(ids)).delete(synchronize_session=False)
    deleted_users = User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
    db.session.commit()

    return BulkDeleteUsersResult(deleted=True, deleted_count=int(deleted_users or 0), reason="ok")

# Количество постов на странице
def get_main_feed(page: int = 1, per_page: int = 20):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)
    query = Post.query.order_by(Post.date_posted.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)

# Удаление поста
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

# Создание поста
@dataclass(frozen=True)
class CreatePostResult:
    created: bool
    post_id: Optional[int]
    reason: str  # "ok" | "empty_content"

def create_post(user_id: int, title: str, content: str) -> CreatePostResult:

    MAX_TITLE_LEN = 100
    MAX_CONTENT_LEN = 2000
    POSTS_PER_MINUTE = 5

    content = (content or "").strip()
    title = (title or "").strip()

    if len(title) > MAX_TITLE_LEN:
        return CreatePostResult(created=False, post_id=None, reason="too_long_title")
    
    if len(content) > MAX_CONTENT_LEN:
        return CreatePostResult(created=False, post_id=None, reason="too_long_content")

    if not content:
        return CreatePostResult(created=False, post_id=None, reason="empty_content")

    # Если title пустой, чтобы не падало заглушка
    if not title:
        title = "Без названия"

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=60)
    
    count = (
        db.session
        .query(func.count(Post.id))
        .filter(
            Post.user_id == user_id,
            Post.date_posted >= window_start
        )
        .scalar()
    )

    if count >= POSTS_PER_MINUTE:
        return CreatePostResult(created=False, post_id=None, reason="rate_limited")

    post = Post(title=title, content=content, user_id=user_id)
    db.session.add(post)
    db.session.commit()

    return CreatePostResult(created=True, post_id=post.id, reason="ok")