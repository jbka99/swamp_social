from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User, Thread
from app.services import (
    create_thread,
    delete_thread,
    get_threads_feed,
    list_user_threads,
    create_update,
    list_updates,
)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    # Remove thread creation form - moved to sidebar
    threads = list_user_threads(user_id=current_user.id)
    return render_template("index.html", threads=threads)

    
@bp.route('/threads')
@login_required
def threads():
    """Thread listing page (replaces old feed behavior)"""
    page = request.args.get('page', 1, type=int)
    pagination = get_threads_feed(page=page, per_page=20)
    return render_template('threads.html', threads=pagination.items, pagination=pagination)

@bp.route('/thread/<int:thread_id>')
@login_required
def thread_detail(thread_id):
    """Single thread detail page"""
    thread = db.session.get(Thread, thread_id)
    if thread is None:
        flash('Тред не найден', 'danger')
        return redirect(url_for('routes.threads'))
    return render_template('thread.html', thread=thread)

@bp.route('/thread/new', methods=['POST'])
@login_required
def thread_new():
    """Create thread from sidebar form"""
    content = request.form.get('content') or request.form.get('body') or ''
    title = request.form.get('title') or ''

    result = create_thread(
        user_id=current_user.id,
        title=title,
        content=content,
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

        result = create_update(
            actor_user_id=current_user.id,
            actor_is_admin=current_user.is_admin,
            title=title,
            content=content,
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

        return redirect(url_for('routes.feed'))

    # Show updates list
    page = request.args.get('page', 1, type=int)
    pagination = list_updates(page=page, per_page=20)
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