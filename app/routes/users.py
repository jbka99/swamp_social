from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User, Post

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
        
        if avatar_link:
            current_user.avatar_url = avatar_link
        else:
            current_user.avatar_url = f"https://api.dicebear.com/7.x/identicon/svg?seed={current_user.username}"

        db.session.commit()

        flash('Профиль обновлен.')
        return redirect(url_for('routes.index'))
    
    return render_template('settings.html', user=current_user)



@bp.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).all()
    return render_template('user.html', user=user, posts=posts)