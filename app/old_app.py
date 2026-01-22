from flask_migrate import Migrate
from config import Config
from flask import Flask, render_template, request, redirect, url_for, flash
from extensions import db, login_manager
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from models.post import Post

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        if title and content:
            new_post = Post(title=title, content=content, author=current_user)
            db.session.add(new_post)
            db.session.commit()
            flash('Пост опубликован!')
            return redirect(url_for('index'))
    
    user_posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.date_posted.desc()).all()
    return render_template('index.html', user=current_user, posts=user_posts)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')
        user = User.query.filter_by(username=uname).first()

        if user and user.check_password(pwd):
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Incorrect login or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        uname = request.form.get('username')
        pwd = request.form.get('password')

        if User.query.filter_by(username=uname).first():
            flash('This user already exists')
            return redirect(url_for('register'))
        
        new_user = User(username = uname)
        new_user.set_password(pwd)
        db.session.add(new_user)
        db.session.commit()

        flash('User succefully created!')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.display_name = request.form.get('display_name')
        current_user.age = request.form.get('age')
        current_user.bio = request.form.get('bio')
        current_user.avatar_url = request.form.get('avatar_url')

        db.session.commit()

        flash('Профиль обновлен.')
        return redirect(url_for('index'))
    return render_template('settings.html', user=current_user)

@app.route('/feed')
@login_required
def feed():
    all_posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('feed.html', posts=all_posts)

if __name__ == '__main__':
    app.run(debug=True)