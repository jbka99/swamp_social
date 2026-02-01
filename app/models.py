from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timezone
from app.extensions import db, login_manager
from sqlalchemy import CheckConstraint, UniqueConstraint

@login_manager.user_loader
def load_user(user_id):
    # return User.query.get(int(user_id)) устаревшая тема
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'user'

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

class PostVote(db.Model):
    __tablename__ = 'post_votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False, index=True)
    value = db.Column(db.SmallInteger, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, 
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uq_post_votes_user_post'),
        CheckConstraint('value in (1, -1)', name='ck_post_vote_value'),
    )

class CommentVote(db.Model):
    __tablename__ = 'comment_votes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=False, index=True)
    value = db.Column(db.SmallInteger, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, 
                            default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint('user_id', 'comment_id', name='uq_comment_votes_user_comment'),
        CheckConstraint('value in (1, -1)', name='ck_comment_vote_value'),
    )
    

class Thread(db.Model):
    __tablename__ = 'post'  # Keep existing table name to avoid migration
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    image_url = db.Column(db.String(256), nullable=True)
    comment_count = db.Column(db.Integer, nullable=False, default=0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    score = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"Thread('{self.title}', '{self.date_posted}')"


class Comment(db.Model):
    __tablename__ = 'comment'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'), nullable=True)
    reply_to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    author = db.relationship('User', lazy=True, foreign_keys=[user_id])
    reply_to_user = db.relationship('User', lazy=True, foreign_keys=[reply_to_user_id])
    thread = db.relationship('Thread', backref=db.backref('comments', lazy=True))
    parent = db.relationship('Comment', remote_side=[id], backref=db.backref('replies', lazy=True))

    image_url = db.Column(db.String(256), nullable=True)

    score = db.Column(db.Integer, nullable=False, default=0)

    @property
    def post(self):
        """Backward compatibility alias for thread"""
        return self.thread

    def __repr__(self):
        return f"<Comment {self.id} user={self.user_id} post={self.post_id} parent={self.parent_id} reply_to={self.reply_to_user_id}>"

class Update(db.Model):
    __tablename__ = 'updates'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    image_path = db.Column(db.String(256), nullable=True)
    
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref='updates', lazy=True)

    def __repr__(self):
        return f"<Update {self.id} '{self.title}'>"