from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User, Thread

import cloudinary.uploader

MAX_AVATAR_MB = 5

@bp.route('/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    f = request.files.get('avatar')
    if not f or f.filename == '':
        flash('Не удалось загрузить файл аватара.')
        return redirect(request.referrer or url_for('routes.user_profile', username='me'))

    if f.mimetype not in ('image/jpeg', 'image/png', 'image/gif', 'image/webp'):
        flash('Неверный формат файла аватара. Разрешены только JPG, PNG, GIF и WebP.', 'error')
        return redirect(request.referrer or url_for('routes.user_profile', username='me'))

    f.stream.seek(0, 2)
    size = f.stream.tell()
    f.stream.seek(0)
    if size > MAX_AVATAR_MB * 1024 * 1024:
        flash(f'Файл слишком большой. Максимальный размер: {MAX_AVATAR_MB}MB.', 'error')
        return redirect(request.referrer or url_for('routes.user_profile', username='me'))

    result = cloudinary.uploader.upload(
        f,
        public_id=f'avatar_{current_user.id}',
        overwrite=True,
        invalidate=True,
        resource_type='image',
        transformation=[
            {'width': 256, 'height': 256, 'crop': 'fill', 'gravity': 'auto'},
            {'quality': 'auto'},
            {'fetch_format': 'auto'},
        ],
    )

    current_user.avatar_url = result['secure_url']
    from app.extensions import db
    db.session.commit()

    flash('Аватар обновлен.', 'success')
    return redirect(request.referrer or url_for('routes.user_profile', username='me'))

@bp.route('/settings', methods = ['POST', 'GET'])
@login_required
def settings():
    if request.method == 'POST':
        age_val = request.form.get('age')
        if age_val and age_val.strip():
            try:
                current_user.age = int(age_val)
            except ValueError:
                pass
        else:
            current_user.age = None

        display_name = request.form.get('display_name', '').strip()    
        current_user.display_name = display_name if display_name else current_user.username

        bio = request.form.get('bio', '').strip()
        current_user.bio = bio if bio else None

        avatar_link = request.form.get('avatar_url', '').strip()
        
        # Only update avatar_url if a new link is explicitly provided
        # Don't overwrite existing uploaded avatar (from /profile/avatar) with dicebear
        # If avatar_link is empty, keep the existing avatar_url unchanged
        if avatar_link:
            current_user.avatar_url = avatar_link
        # Note: If avatar_link is empty, we preserve the existing avatar_url
        # This allows users to keep their uploaded avatars even if the URL field is cleared

        db.session.commit()

        flash('Профиль обновлен.')
        return redirect(url_for('routes.user_profile', username='me'))
    
    return render_template('settings.html', user=current_user)



@bp.route('/user/<username>')
@login_required
def user_profile(username):
    # Handle /user/me redirect to current user's profile
    if username.lower() in ['me', '{me}']:
        if not current_user.is_authenticated:
            flash('Войдите, чтобы просмотреть свой профиль.')
            return redirect(url_for('routes.login'))
        return redirect(url_for('routes.user_profile', username=current_user.username))
    
    user = User.query.filter_by(username=username).first_or_404()
    threads = Thread.query.filter_by(author=user).order_by(Thread.date_posted.desc()).all()
    
    # Set breadcrumbs
    if current_user.is_authenticated and username == current_user.username:
        breadcrumbs = [
            {'label': 'Мой профиль', 'url': ''}
        ]
    else:
        breadcrumbs = [
            {'label': 'Профиль', 'url': ''},
            {'label': username, 'url': ''}
        ]
    
    return render_template('user.html', user=user, threads=threads, breadcrumbs=breadcrumbs)