from functools import wraps

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.models import User
from app.services import (
    admin_delete_all_posts_from_user,
    admin_delete_user,
    admin_bulk_delete_users,
)


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('routes.login'))

        # ВАЖНО: is_admin, без опечаток
        if not bool(getattr(current_user, 'is_admin', False)):
            flash('Доступ запрещён: только для администраторов.', 'danger')
            return redirect(url_for('routes.feed'))

        return view(*args, **kwargs)
    return wrapper


@bp.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.order_by(User.id.asc()).all()
    breadcrumbs = [
        {'label': 'Админка', 'url': ''}
    ]
    return render_template('admin_users.html', users=users, breadcrumbs=breadcrumbs)


@bp.route('/admin/user/<int:user_id>/posts/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user_posts(user_id: int):
    result = admin_delete_all_posts_from_user(
        target_user_id=user_id,
        actor_is_admin=bool(getattr(current_user, 'is_admin', False)),
    )

    if result.deleted:
        flash(f'Удалено постов: {result.deleted_count}', 'success')
    elif result.reason == 'not_found':
        flash('Пользователь не найден.', 'warning')
    else:
        flash('Недостаточно прав.', 'danger')

    return redirect(url_for('routes.admin_users'))


@bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user_account(user_id: int):
    result = admin_delete_user(
        target_user_id=user_id,
        actor_user_id=current_user.id,
        actor_is_admin=bool(getattr(current_user, 'is_admin', False)),
    )

    if result.deleted:
        flash('Аккаунт удалён.', 'success')
    elif result.reason == 'self_delete_blocked':
        flash('Нельзя удалить свой аккаунт через админку.', 'warning')
    elif result.reason == 'not_found':
        flash('Пользователь не найден.', 'warning')
    else:
        flash('Недостаточно прав.', 'danger')

    return redirect(url_for('routes.admin_users'))


@bp.route('/admin/users/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_users_bulk():
    ids = request.form.getlist('user_ids')

    result = admin_bulk_delete_users(
        target_user_ids=ids,
        actor_user_id=current_user.id,
        actor_is_admin=bool(getattr(current_user, 'is_admin', False)),
    )

    if result.deleted:
        flash(f'Удалено аккаунтов: {result.deleted_count}', 'success')
    elif result.reason == 'empty':
        flash('Не выбраны пользователи (или выбран только ваш аккаунт).', 'warning')
    else:
        flash('Недостаточно прав.', 'danger')

    return redirect(url_for('routes.admin_users'))
