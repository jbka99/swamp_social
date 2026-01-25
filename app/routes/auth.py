from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required

from app.routes import bp
from app.extensions import db
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.user_profile', username='me'))

    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')
        user = User.query.filter_by(username=uname).first()

        if user and user.check_password(pwd):
            login_user(user)
            from app.services import ensure_admin_flag
            ensure_admin_flag(user)
            return redirect(url_for('routes.user_profile', username='me'))
        
        flash('Неверный логин или пароль', 'danger')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')

        if User.query.filter_by(username=uname).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return redirect(url_for('routes.register'))
        
        # Password validation: minimum 8 characters
        if not pwd or len(pwd) < 8:
            flash('Пароль должен содержать минимум 8 символов', 'danger')
            return redirect(url_for('routes.register'))
        
        new_user = User(username = uname)
        new_user.set_password(pwd)
        db.session.add(new_user)
        db.session.commit()

        flash('Пользователь успешно создан!', 'success')
        return redirect(url_for('routes.login'))

    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))