from dataclasses import dataclass
from app.extensions import db
from app.models import Thread, User, Update, Comment
from typing import Optional, Iterable
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from flask import current_app

# Backward compatibility alias
Post = Thread

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
        Thread.query
        .filter(Thread.user_id == user.id)
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
    
    # Сначала удаляю треды, а потом пользователя
    Thread.query.filter(Thread.user_id == user.id).delete(synchronize_session=False)
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

    actor_id = int(actor_user_id)

    ids: list[int] = []
    for x in target_user_ids:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue

    # unique + skip actor
    ids = sorted({x for x in ids if x != actor_id})

    if not ids:
        return BulkDeleteUsersResult(deleted=False, deleted_count=0, reason="empty")

    # load targets and delete via ORM (stable for session/tests)
    users = User.query.filter(User.id.in_(ids)).all()

    # delete threads first (fast path)
    Thread.query.filter(Thread.user_id.in_([u.id for u in users])).delete(synchronize_session=False)

    for u in users:
        db.session.delete(u)

    db.session.commit()
    return BulkDeleteUsersResult(deleted=True, deleted_count=len(users), reason="ok")

# Thread listing (replaces old feed)
def get_threads_feed(page: int = 1, per_page: int = 20):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)
    query = Thread.query.order_by(Thread.date_posted.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)

# Backward compatibility alias
get_main_feed = get_threads_feed

# Threads of a specific user
def list_user_threads(user_id: int, limit: int = 50):
    user_id = int(user_id)
    limit = min(max(int(limit), 1), 100)

    return (
        Thread.query
        .filter(Thread.user_id == user_id)
        .order_by(Thread.date_posted.desc())
        .limit(limit)
        .all()
    )

# Backward compatibility alias
list_user_posts = list_user_threads

# Thread deletion
@dataclass(frozen=True)
class DeleteThreadResult:
    deleted: bool
    reason: str  # "ok" | "not_found" | "forbidden"

# Backward compatibility alias
DeletePostResult = DeleteThreadResult

def delete_thread(thread_id: int, actor_user_id: int, actor_is_admin: bool) -> DeleteThreadResult:
    thread = db.session.get(Thread, int(thread_id))
    if thread is None:
        return DeleteThreadResult(deleted=False, reason="not_found")

    can_delete = actor_is_admin or (thread.user_id == actor_user_id)
    if not can_delete:
        return DeleteThreadResult(deleted=False, reason="forbidden")

    # delete comments first
    db.session.query(Comment).filter(Comment.post_id == thread_id).delete(synchronize_session=False)

    db.session.delete(thread)
    db.session.commit()
    return DeleteThreadResult(deleted=True, reason="ok")

# Backward compatibility alias
delete_post = delete_thread

# Thread creation
@dataclass(frozen=True)
class CreateThreadResult:
    created: bool
    thread_id: Optional[int]
    reason: str  # "ok" | "empty_content" | "too_long_title" | "too_long_content" | "rate_limited"

# Backward compatibility alias
CreatePostResult = CreateThreadResult

def create_thread(user_id: int, title: str, content: str) -> CreateThreadResult:
    MAX_TITLE_LEN = 100
    MAX_CONTENT_LEN = 2000
    THREADS_PER_MINUTE = 5

    content = (content or "").strip()
    title = (title or "").strip()

    if len(title) > MAX_TITLE_LEN:
        return CreateThreadResult(created=False, thread_id=None, reason="too_long_title")
    
    if len(content) > MAX_CONTENT_LEN:
        return CreateThreadResult(created=False, thread_id=None, reason="too_long_content")

    if not content:
        return CreateThreadResult(created=False, thread_id=None, reason="empty_content")

    # Если title пустой, чтобы не падало заглушка
    if not title:
        title = "Без названия"

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=60)
    
    count = (
        db.session
        .query(func.count(Thread.id))
        .filter(
            Thread.user_id == user_id,
            Thread.date_posted >= window_start
        )
        .scalar()
    )

    if count >= THREADS_PER_MINUTE:
        return CreateThreadResult(created=False, thread_id=None, reason="rate_limited")

    thread = Thread(title=title, content=content, user_id=user_id)
    db.session.add(thread)
    db.session.commit()

    return CreateThreadResult(created=True, thread_id=thread.id, reason="ok")

# Backward compatibility alias
create_post = create_thread

# Update services
@dataclass(frozen=True)
class CreateUpdateResult:
    created: bool
    update_id: Optional[int]
    reason: str  # "ok" | "forbidden" | "empty_content" | "too_long_title" | "too_long_content"

def create_update(actor_user_id: int, actor_is_admin: bool, title: str, content: str) -> CreateUpdateResult:
    if not actor_is_admin:
        return CreateUpdateResult(created=False, update_id=None, reason="forbidden")
    
    MAX_TITLE_LEN = 200
    MAX_CONTENT_LEN = 5000

    content = (content or "").strip()
    title = (title or "").strip()

    if len(title) > MAX_TITLE_LEN:
        return CreateUpdateResult(created=False, update_id=None, reason="too_long_title")
    
    if len(content) > MAX_CONTENT_LEN:
        return CreateUpdateResult(created=False, update_id=None, reason="too_long_content")

    if not content:
        return CreateUpdateResult(created=False, update_id=None, reason="empty_content")

    if not title:
        return CreateUpdateResult(created=False, update_id=None, reason="empty_content")

    update = Update(title=title, content=content, author_id=actor_user_id)
    db.session.add(update)
    db.session.commit()

    return CreateUpdateResult(created=True, update_id=update.id, reason="ok")

def list_updates(page: int = 1, per_page: int = 20):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)
    query = Update.query.order_by(Update.created_at.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)

# Comment services

def create_comment(*, thread_id: int, author_id: int, content: str, parent_id: Optional[int] = None):
    content = (content or "").strip()
    if not content:
        return {"ok": False, "error": "empty", "comment_id": None}

    thread = db.session.get(Thread, int(thread_id))
    if thread is None:
        return {"ok": False, "error": "not_found", "comment_id": None}

    # If parent_id is provided, verify the parent comment exists and belongs to the same thread
    if parent_id is not None:
        parent_comment = db.session.get(Comment, int(parent_id))
        if parent_comment is None:
            return {"ok": False, "error": "parent_not_found", "comment_id": None}
        if parent_comment.post_id != thread_id:
            return {"ok": False, "error": "parent_mismatch", "comment_id": None}

    # Thread.__tablename__ == 'post', so use post_id FK
    comment = Comment(content=content, user_id=author_id, post_id=thread_id, parent_id=parent_id)
    db.session.add(comment)
    db.session.commit()
    return {"ok": True, "error": None, "comment_id": comment.id} 