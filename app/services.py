from app.models import Post

def get_main_feed():
    from app.models import Post
    return Post.query.order_by(Post.date_posted.desc()).all()

def create_post(user_id, text):
    pass