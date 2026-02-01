import os
import cloudinary

from app import create_app, db, socketio
from app.models import User, Thread


def init_cloudinary() -> None:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )


app = create_app()
init_cloudinary()

debug_mode = os.environ.get("FLASK_DEBUG", "0").lower() in {"true", "1", "t", "yes", "y"}


@app.shell_context_processor
def make_shell_context():
    # "Post" alias оставляю, но поправляю (у тебя было Thread вместо Post)
    return {"db": db, "User": User, "Thread": Thread}
    # Если реально нужен Post alias:
    # from app.models import Post
    # return {"db": db, "User": User, "Thread": Thread, "Post": Post}


if __name__ == "__main__":
    # Для локального запуска python run.py (не хостинг)
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug_mode)