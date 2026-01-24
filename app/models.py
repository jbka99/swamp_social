from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    # return User.query.get(int(user_id)) устаревшая тема
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)

    display_name = db.Column(db.String(64))
    age = db.Column(db.Integer)
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(256))

    threads = db.relationship('Thread', backref='author', lazy=True)

    @property
    def posts(self):
        """Backward compatibility alias for threads"""
        return self.threads

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Thread(db.Model):
    __tablename__ = 'post'  # Keep existing table name to avoid migration
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Thread('{self.title}', '{self.date_posted}')"

# Keep Post alias for backward compatibility during transition
Post = Thread

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    author = db.relationship('User', lazy=True)
    thread = db.relationship('Thread', backref=db.backref('comments', lazy=True))

    @property
    def post(self):
        """Backward compatibility alias for thread"""
        return self.thread

    def __repr__(self):
        return f"<Comment {self.id} user={self.user_id} post={self.post_id}>"

class Update(db.Model):
    __tablename__ = 'update'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    image_path = db.Column(db.String(256), nullable=True)
    
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='updates', lazy=True)

    def __repr__(self):
        return f"<Update {self.id} '{self.title}'>"