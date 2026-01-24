from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User
from app.services import (
    create_post as create_post_service,
    delete_post as delete_post_service,
    get_main_feed,
    list_user_posts,
)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        content = request.form.get('content') or request.form.get('body') or ''
        title = request.form.get('title') or ''

        result = create_post_service(
            user_id=current_user.id,
            title=title,
            content=content,
        )

        if result.created:
            flash('Пост успешно создан', 'success')
        elif result.reason == "empty_content":
            flash('Пост не может быть пустым', 'danger')
        elif result.reason == "too_long_title":
            flash('Заголовок поста слишком длинный', 'danger')
        elif result.reason == "too_long_content":
            flash('Пост слишком длинный', 'danger')
        elif result.reason == "rate_limited":
            flash('Слишком много постов, подождите минутку', 'warning')

        return redirect(url_for('routes.index'))

    posts = list_user_posts(user_id=current_user.id)
    return render_template("index.html", posts=posts)

    
@bp.route('/feed')
@login_required
def feed():
    page = request.args.get('page', 1, type=int)
    pagination = get_main_feed(page=page, per_page=20)
    return render_template('feed.html', posts=pagination.items, pagination=pagination)

@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    result = delete_post_service(
        post_id=post_id,
        actor_user_id=current_user.id,
        actor_is_admin=bool(getattr(current_user, "is_admin", False)),
    )

    if result.deleted:
        flash('Пост удален.')
    elif result.reason == "forbidden":
        flash('Вы не можете удалить чужой пост!')
    else:
        flash('Пост не найден.')

    return redirect(request.referrer or url_for('routes.index'))