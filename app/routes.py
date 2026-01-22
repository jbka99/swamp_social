from flask import Blueprint, render_template, flash, redirect, url_for, request
from app.extensions import db
from app.models import Post, User
from flask_login import current_user, login_required, login_user, logout_user
from app.services import get_main_feed

bp = Blueprint('routes', __name__)

    

@bp.before_app_request
def setup_db():
    # Эта функция будет запускаться ОДИН РАЗ перед любым запросом
    # и пытаться создать таблицы
    db.create_all()

@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    
    me = User.query.filter_by(username='admin').first()
    if me and not me.is_admin:
        me.is_admin = True
        db.session.commit()

    if request.method == 'POST':
        body = request.form.get('body')
        if body:
            new_post = Post(title=request.form.get('title'), content=body, author=current_user)
            db.session.add(new_post)
            db.session.commit()
            flash('Пост опубликован!')
            return redirect(url_for('routes.index'))
        
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('index.html', posts=posts, user=current_user)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('routes.index'))

    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')
        user = User.query.filter_by(username=uname).first()

        if user and user.check_password(pwd):
            login_user(user)
            return redirect(url_for('routes.index'))
        
        flash('Incorrect login or password')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')

        if User.query.filter_by(username=uname).first():
            flash('This user already exists')
            return redirect(url_for('routes.register'))
        
        new_user = User(username = uname)
        new_user.set_password(pwd)
        db.session.add(new_user)
        db.session.commit()

        flash('User succefully created!')
        return redirect(url_for('routes.login'))

    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))

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

@bp.route('/feed')
@login_required
def feed():
    all_posts = get_main_feed()
    return render_template('feed.html', posts=all_posts)

@bp.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.author != current_user:
        flash('Вы не можете удалить чужой пост!')
        return redirect(url_for('routes.index'))
    
    db.session.delete(post)
    db.session.commit()
    flash('Пост удален.')
    
    return redirect(request.referrer or url_for('routes.index'))

@bp.route('/user/<username>')
@login_required
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).all()
    return render_template('user.html', user=user, posts=posts)