from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload, selectinload
import cloudinary.uploader

from app.routes import bp
from app.extensions import db
from app.models import User, Thread, Comment, PostVote, CommentVote
from app.services import (
    create_thread,
    delete_thread,
    get_threads_feed,
    list_user_threads,
    create_update,
    list_updates,
    create_comment,
    delete_comment,
    vote_post,
    vote_comment,
)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
def index():
    # Redirect to user profile instead of separate index page
    if current_user.is_authenticated:
        return redirect(url_for('routes.user_profile', username='me'))
    else:
        return redirect(url_for('routes.login'))

    
@bp.route('/threads')
@login_required
def threads():
    """Thread listing page (replaces old feed behavior)"""
    sort = request.args.get('sort', 'new')
    page = request.args.get('page', 1, type=int)

    pagination = get_threads_feed(
        page=page, 
        per_page=20, 
        sort=sort
    )
    # Load current user's votes for threads so highlight persists after refresh
    if pagination.items and current_user.is_authenticated:
        post_ids = [t.id for t in pagination.items]
        votes = PostVote.query.filter(
            PostVote.user_id == current_user.id,
            PostVote.post_id.in_(post_ids)
        ).all()
        votes_by_post = {v.post_id: v.value for v in votes}
        for t in pagination.items:
            t.my_vote = votes_by_post.get(t.id, 0)

    return render_template(
        'threads.html', 
        threads=pagination.items, 
        pagination=pagination, 
        sort=sort
    )

@bp.route('/thread/<int:thread_id>')
@login_required
def thread_detail(thread_id):
    """Single thread detail page"""
    # Eager-load comments, their authors, and replies to avoid N+1 queries
    from sqlalchemy.orm import selectinload
    
    thread = (
        db.session.query(Thread)
        .options(
            joinedload(Thread.comments).joinedload(Comment.author),
            joinedload(Thread.comments).joinedload(Comment.reply_to_user),
            joinedload(Thread.comments).selectinload(Comment.replies).joinedload(Comment.author),
            joinedload(Thread.comments).selectinload(Comment.replies).joinedload(Comment.reply_to_user)
        )
        .filter(Thread.id == thread_id)
        .first()
    )
    if thread is None:
        flash('Тред не найден', 'danger')
        return redirect(url_for('routes.threads'))

    # Current user's vote for thread and comments (for highlight on load)
    thread_my_vote = 0
    comment_my_votes = {}
    if current_user.is_authenticated:
        pv = PostVote.query.filter_by(user_id=current_user.id, post_id=thread.id).first()
        thread_my_vote = pv.value if pv else 0
        comment_ids = [c.id for c in thread.comments]
        if comment_ids:
            cvs = CommentVote.query.filter(
                CommentVote.user_id == current_user.id,
                CommentVote.comment_id.in_(comment_ids)
            ).all()
            comment_my_votes = {v.comment_id: v.value for v in cvs}
    thread.my_vote = thread_my_vote
    for c in thread.comments:
        c.my_vote = comment_my_votes.get(c.id, 0)
    
    # Separate top-level comments (no parent) from replies
    top_level_comments = [c for c in thread.comments if c.parent_id is None]
    # Sort top-level comments by date
    top_level_comments.sort(key=lambda c: c.date_posted)
    # Sort replies within each comment
    for comment in thread.comments:
        if comment.replies:
            comment.replies.sort(key=lambda r: r.date_posted)
    
    breadcrumbs = [
        {'label': 'Треды', 'url': url_for('routes.threads')},
        {'label': (thread.title[:50] + ('...' if len(thread.title) > 50 else '')) if thread.title else 'Тред', 'url': ''}
    ]
    return render_template('thread.html', thread=thread, top_level_comments=top_level_comments, breadcrumbs=breadcrumbs)

@bp.route('/thread/new', methods=['POST'])
@login_required
def thread_new():
    """Create thread from sidebar form"""
    content = request.form.get('content') or request.form.get('body') or ''
    title = request.form.get('title') or ''
    image_file = request.files.get('image')

    result = create_thread(
        user_id=current_user.id,
        title=title,
        content=content,
        image_file=image_file,
    )

    if result.created:
        flash('Тред успешно создан', 'success')
        return redirect(url_for('routes.thread_detail', thread_id=result.thread_id))
    elif result.reason == "empty_content":
        flash('Тред не может быть пустым', 'danger')
    elif result.reason == "too_long_title":
        flash('Заголовок треда слишком длинный', 'danger')
    elif result.reason == "too_long_content":
        flash('Тред слишком длинный', 'danger')
    elif result.reason == "rate_limited":
        flash('Слишком много тредов, подождите минутку', 'warning')
    elif result.reason == "bad_image_type":
        flash('Неверный формат изображения. Разрешены только JPG, PNG, GIF и WebP.', 'danger')
    elif result.reason == "image_too_large":
        flash('Изображение слишком большое. Максимальный размер: 10MB.', 'danger')
    elif result.reason == "image_upload_failed":
        flash('Не удалось загрузить изображение.', 'danger')

    return redirect(request.referrer or url_for('routes.threads'))

@bp.route('/feed', methods=['GET', 'POST'])
@login_required
def feed():
    """Info panel showing updates/changelog"""
    if request.method == 'POST':
        # Admin-only: create update
        if not current_user.is_admin:
            flash('Только администраторы могут создавать обновления', 'danger')
            return redirect(url_for('routes.feed'))
        
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        image_file = request.files.get('image')

        result = create_update(
            actor_user_id=current_user.id,
            actor_is_admin=current_user.is_admin,
            title=title,
            content=content,
            image_file=image_file,
        )

        if result.created:
            flash('Обновление успешно создано', 'success')
        elif result.reason == "forbidden":
            flash('Недостаточно прав', 'danger')
        elif result.reason == "empty_content":
            flash('Содержимое не может быть пустым', 'danger')
        elif result.reason == "too_long_title":
            flash('Заголовок слишком длинный', 'danger')
        elif result.reason == "too_long_content":
            flash('Содержимое слишком длинное', 'danger')
        elif result.reason == "bad_image_type":
            flash('Неверный формат изображения. Разрешены только JPG, PNG, GIF и WebP.', 'danger')
        elif result.reason == "image_too_large":
            flash('Изображение слишком большое. Максимальный размер: 10MB.', 'danger')
        elif result.reason == "image_upload_failed":
            flash('Не удалось загрузить изображение.', 'danger')

        return redirect(url_for('routes.feed'))

    # Show updates list
    page = request.args.get('page', 1, type=int)
    pagination = list_updates(page=page, per_page=20)
    # Feed page doesn't show breadcrumbs (it's the main page)
    return render_template('feed.html', updates=pagination.items, pagination=pagination, is_admin=current_user.is_admin)

@bp.route('/thread/<int:thread_id>/delete', methods=['POST'])
@login_required
def delete_thread_route(thread_id):
    result = delete_thread(
        thread_id=thread_id,
        actor_user_id=current_user.id,
        actor_is_admin=bool(getattr(current_user, "is_admin", False)),
    )

    if result.deleted:
        flash('Тред удален.')
    elif result.reason == "forbidden":
        flash('Вы не можете удалить чужой тред!')
    else:
        flash('Тред не найден.')

    return redirect(request.referrer or url_for('routes.threads'))

# Backward compatibility route alias
@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    return delete_thread_route(post_id)


@bp.route('/thread/<int:thread_id>/comment', methods=['POST'])
@login_required
def add_comment(thread_id: int):
    content = request.form.get('content', "").strip()
    parent_id = request.form.get('parent_id', type=int)  # None if not provided
    reply_to_user_id = request.form.get('reply_to_user_id', type=int)  # None if not provided
    image = request.files.get('image')

    result = create_comment(
        thread_id=thread_id, 
        author_id=current_user.id, 
        content=content,
        parent_id=parent_id,
        reply_to_user_id=reply_to_user_id,
        image_file=request.files.get('image'),
    )

    if not result["ok"]:
        if result["error"] == "empty":
            flash("Комментарий пустой.", "warning")
        elif result["error"] == "not_found":
            flash("Тред не найден.", "danger")
        elif result["error"] == "parent_not_found":
            flash("Родительский комментарий не найден.", "danger")
        elif result["error"] == "parent_mismatch":
            flash("Ошибка: комментарий не принадлежит этому треду.", "danger")
        elif result["error"] == "reply_to_user_not_found":
            flash("Пользователь, на которого отвечают, не найден.", "danger")
        elif result["error"] == "bad_type":
            flash("Неверный формат изображения. Разрешены только JPG, PNG, GIF и WebP.", "danger")
        elif result["error"] == "too_large":
            flash("Изображение слишком большое. Максимальный размер: 10MB.", "danger")
        elif result["error"] == "upload_failed":
            flash("Не удалось загрузить изображение.", "danger")
        else:
            flash("Неизвестная ошибка.", "danger")

    return redirect(url_for('routes.thread_detail', thread_id=thread_id))

@bp.route('/thread/<int:thread_id>/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment_route(thread_id: int, comment_id: int):
    result = delete_comment(
        thread_id=thread_id,
        comment_id=comment_id,
        actor_user_id=current_user.id,
        actor_is_admin=bool(getattr(current_user, "is_admin", False)),
    )

    if result.deleted:
        flash('Комментарий удален.', 'success')
    elif result.reason == "forbidden":
        flash('Вы не можете удалить чужой комментарий!', 'danger')
    elif result.reason == "not_found":
        flash('Комментарий не найден.', 'danger')
    else:
        flash('Неизвестная ошибка.', 'danger')
    
    return redirect(url_for('routes.thread_detail', thread_id=thread_id))

# COMMENT COUNT                                                  
# @bp.route('/thread/<int:thread_id>/comment/count', methods=['GET'])
# @login_required
# def get_comment_count(thread_id: int):
#     Thread.query.get_or_404(thread_id) # 404 если треда нет
#     comment_count = Comment.query.filter_by(post_id=thread_id).count()
#     return jsonify({"thread_id": thread_id, "comment_count": comment_count})

# votes
@bp.route('/thread/<int:thread_id>/vote', methods=['POST'])
@login_required
def vote_post_route(thread_id: int):
    data = request.get_json(silent=True) or {}
    value = data.get('value')

    if value not in (-1, 1):
        return jsonify({"success": False, "reason": "invalid_value"}), 400

    result = vote_post(post_id=thread_id, user_id=current_user.id, value=value)

    if result.success:
        return jsonify({"success": True, "score": result.score, "my_vote": result.my_vote})

    return jsonify({"success": False, "reason": result.reason}), 400

@bp.route('/thread/<int:thread_id>/comment/<int:comment_id>/vote', methods=['POST'])
@login_required
def vote_comment_route(thread_id: int, comment_id: int):
    data = request.get_json(silent=True) or {}
    value = data.get('value')

    if value not in (-1, 1):
        return jsonify({"success": False, "reason": "invalid_value"}), 400

    result = vote_comment(comment_id=comment_id, user_id=current_user.id, value=value)
    
    if result.success:
        return jsonify({"success": True, "score": result.score, "my_vote": result.my_vote})

    return jsonify({"success": False, "reason": result.reason}), 400

