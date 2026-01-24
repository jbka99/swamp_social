Открывается главная страница 
v4 - OK
v5 - OK

Регистрация нового пользователя
v4 - OK
v5 - OK

Логин
v4 - OK
v5 - OK

Переход в профиль
v4 - OK
v5 - OK

Создание поста (текст)
v4 - OK
v5 - OK

Пост появляется в ленте/профиле
v4 - OK
v5 - OK

Логаут
v4 - OK
v5 - OK

## Comment Table Migration Smoke Test

### Verify migration is applied:
```bash
# In Docker container
docker compose exec web flask db upgrade

# Should show migration b2c3d4e5f6a7 applied (or "Already at head")
# Verify table exists:
docker compose exec web flask shell
>>> from app.extensions import db
>>> from sqlalchemy import inspect
>>> inspector = inspect(db.engine)
>>> 'comment' in inspector.get_table_names()
True
```

### Verify comment functionality:
1. Navigate to `/thread/1` (or any existing thread)
2. Page should load without "no such table: comment" error
3. Comment form should be visible (if logged in)
4. Submit a comment - should redirect back to thread page
5. Comment should appear in the comments list below the thread

### Migration details:
- Migration file: `migrations/versions/b2c3d4e5f6a7_add_comment_table.py`
- Creates table: `comment` (not `comments`)
- Columns: id, content, date_posted, user_id, post_id
- Foreign keys: user_id → user.id, post_id → post.id
- Indexes: ix_comment_post_id, ix_comment_user_id
- Safe: Only creates table if it doesn't exist