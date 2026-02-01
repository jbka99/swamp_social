from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, Any, Dict
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import func
import cloudinary.uploader

from app.extensions import db
from app.models import Thread, User, Update, Comment, PostVote, CommentVote

AlLOWED_MIME = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024 # 10MB

def upload_content_image(file, *, folder: str) -> Dict[str, Any]:
    if not file or getattr(file, "filename", "") == "":
        return {"ok": True, "url": None, "public_id": None, "error": None}

    # MIME
    mime = getattr(file, "mimetype", None)
    if mime not in AlLOWED_MIME:
        return {"ok": False, "url": None, "public_id": None, "error": "bad_type"}

    # SIZE
    file.stream.seek(0, 2)
    size = file.stream.tell()
    file.stream.seek(0)
    if size > MAX_BYTES:
        return {"ok": False, "url": None, "public_id": None, "error": "too_large"}
    
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image",
            overwrite=False,
            unique_filename=True,
            transformation=[
                {"quality": "auto:eco"},
                {"fetch_format": "auto"},
                {"width": 520, "height": 520, "crop": "limit"},
            ],
        )
        return {
            "ok": True,
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "error": None,
        }
    except Exception:
        current_app.logger.exception("Failed to upload content image")
        return {"ok": False, "url": None, "public_id": None, "error": "upload_failed"}


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

@dataclass(frozen=True)
class DeleteCommentResult:
    deleted: bool
    reason: str # "ok" | "not_found" | "forbidden"

def delete_comment(thread_id: int, comment_id: int, actor_user_id: int, actor_is_admin: bool) -> DeleteCommentResult:
    comment = db.session.get(Comment, int(comment_id))
    if comment is None:
        return DeleteCommentResult(deleted=False, reason="not_found")

    if comment.post_id != thread_id:
        return DeleteCommentResult(deleted=False, reason="not_found")

    if (not actor_is_admin) and (comment.user_id != int(actor_user_id)):
        return DeleteCommentResult(deleted=False, reason="forbidden")
    
    # Update comment count for the thread
    thread = db.session.get(Thread, int(thread_id))
    if thread is None:
        return DeleteCommentResult(deleted=False, reason="not_found")

    thread.comment_count = max(0, (thread.comment_count or 0) - 1)
    
    db.session.delete(comment)
    db.session.commit()
    return DeleteCommentResult(deleted=True, reason="ok")

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
def get_threads_feed(page: int = 1, per_page: int = 20, sort: str = "new"):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)

    query = Thread.query

    if sort == "top":
        query = query.order_by(Thread.score.desc(), Thread.date_posted.desc())
    elif sort == "discussed":
        query = query.order_by(Thread.comment_count.desc(), Thread.date_posted.desc())
    else: # new
        query = query.order_by(Thread.date_posted.desc())
        
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

def create_thread(user_id: int, title: str, content: str, image_file=None) -> CreateThreadResult:
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

    # Upload image if provided
    image_url = None
    if image_file:
        upload_result = upload_content_image(image_file, folder="threads")
        if not upload_result["ok"]:
            error = upload_result.get("error", "upload_failed")
            if error == "bad_type":
                return CreateThreadResult(created=False, thread_id=None, reason="bad_image_type")
            elif error == "too_large":
                return CreateThreadResult(created=False, thread_id=None, reason="image_too_large")
            else:
                return CreateThreadResult(created=False, thread_id=None, reason="image_upload_failed")
        image_url = upload_result.get("url")

    thread = Thread(title=title, content=content, user_id=user_id, image_url=image_url)
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

def create_update(actor_user_id: int, actor_is_admin: bool, title: str, content: str, image_file=None) -> CreateUpdateResult:
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

    # Upload image if provided
    image_path = None
    if image_file:
        upload_result = upload_content_image(image_file, folder="updates")
        if not upload_result["ok"]:
            error = upload_result.get("error", "upload_failed")
            if error == "bad_type":
                return CreateUpdateResult(created=False, update_id=None, reason="bad_image_type")
            elif error == "too_large":
                return CreateUpdateResult(created=False, update_id=None, reason="image_too_large")
            else:
                return CreateUpdateResult(created=False, update_id=None, reason="image_upload_failed")
        image_path = upload_result.get("url")

    update = Update(title=title, content=content, author_id=actor_user_id, image_path=image_path)
    db.session.add(update)
    db.session.commit()

    return CreateUpdateResult(created=True, update_id=update.id, reason="ok")

def list_updates(page: int = 1, per_page: int = 20):
    page = max(int(page), 1)
    per_page = min(max(int(per_page), 1), 50)
    query = Update.query.order_by(Update.created_at.desc())
    return query.paginate(page=page, per_page=per_page, error_out=False)

# Comment services

def create_comment(
    *, 
    thread_id: int, 
    author_id: int, 
    content: str, 
    parent_id: Optional[int] = None, 
    reply_to_user_id: Optional[int] = None,
    image_file=None,
    ):
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

    # If reply_to_user_id is provided, verify the user exists
    if reply_to_user_id is not None:
        reply_to_user = db.session.get(User, int(reply_to_user_id))
        if reply_to_user is None:
            return {"ok": False, "error": "reply_to_user_not_found", "comment_id": None}

    # Upload image if provided
    image_url = None
    if image_file:
        upload_result = upload_content_image(image_file, folder="comments")
        if not upload_result["ok"]:
            return {"ok": False, "error": upload_result.get("error", "upload_failed"), "comment_id": None}
        image_url = upload_result.get("url")

    # Update comment count for the thread
    thread.comment_count = (thread.comment_count or 0) + 1

    # Thread.__tablename__ == 'post', so use post_id FK
    comment = Comment(
        content=content, 
        user_id=author_id, 
        post_id=thread_id, 
        parent_id=parent_id,
        reply_to_user_id=reply_to_user_id,
        image_url=image_url,
    )
    db.session.add(comment)
    db.session.commit()
    return {"ok": True, "error": None, "comment_id": comment.id}


@dataclass(frozen=True)
class VotePostResult:
    success: bool
    reason: str  # "ok" | "not_found" | "invalid_value"
    score: Optional[int] = None
    my_vote: Optional[int] = None  # 1, -1, or 0 (removed)


@dataclass(frozen=True)
class VoteCommentResult:
    success: bool
    reason: str  # "ok" | "not_found" | "invalid_value"
    score: Optional[int] = None
    my_vote: Optional[int] = None  # 1, -1, or 0 (removed)


def vote_post(post_id: int, user_id: int, value: int) -> VotePostResult:
    post = db.session.get(Post, int(post_id))

    if post is None:
        return VotePostResult(success=False, reason="not_found")
    if value not in [-1, 1]:
        return VotePostResult(success=False, reason="invalid_value")

    post_vote = (
        PostVote.query
        .filter_by(user_id=user_id, post_id=post_id)
        .first()
    )
    old = post_vote.value if post_vote else 0

    if post_vote and post_vote.value == value:
        db.session.delete(post_vote)
        new = 0
    else:
        new = value
        if post_vote is None:
            post_vote = PostVote(user_id=user_id, post_id=post_id, value=value)
            db.session.add(post_vote)
        else:
            post_vote.value = value

    post.score += (new - old)
    db.session.commit()
    return VotePostResult(success=True, reason="ok", score=post.score, my_vote=new)

def vote_comment(comment_id: int, user_id: int, value: int) -> VoteCommentResult:
    comment = db.session.get(Comment, int(comment_id))
    if comment is None:
        return VoteCommentResult(success=False, reason="not_found")
    if value not in [-1, 1]:
        return VoteCommentResult(success=False, reason="invalid_value")
    comment_vote = (
        CommentVote.query
        .filter_by(user_id=user_id, comment_id=comment_id)
        .first()
    )
    old = comment_vote.value if comment_vote else 0
    if comment_vote and comment_vote.value == value:
        db.session.delete(comment_vote)
        new = 0
    else:
        new = value
        if comment_vote is None:
            comment_vote = CommentVote(user_id=user_id, comment_id=comment_id, value=value)
            db.session.add(comment_vote)
        else:
            comment_vote.value = value
    comment.score += (new - old)
    db.session.commit()
    return VoteCommentResult(success=True, reason="ok", score=comment.score, my_vote=new)