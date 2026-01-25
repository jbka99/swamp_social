"""add image_url to post and comment

Revision ID: 4ebaa2c5886e
Revises: d4e5f6a7b8c9
Create Date: 2026-01-25 20:27:50.870486

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '4ebaa2c5886e'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade():
    # Check if 'post' table exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Add image_url to post table
    if 'post' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('post')]
        if 'image_url' not in columns:
            is_sqlite = bind.dialect.name == 'sqlite'
            if is_sqlite:
                with op.batch_alter_table('post', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('image_url', sa.String(256), nullable=True))
            else:
                op.add_column('post', sa.Column('image_url', sa.String(256), nullable=True))
    
    # Add image_url to comment table
    if 'comment' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('comment')]
        if 'image_url' not in columns:
            is_sqlite = bind.dialect.name == 'sqlite'
            if is_sqlite:
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('image_url', sa.String(256), nullable=True))
            else:
                op.add_column('comment', sa.Column('image_url', sa.String(256), nullable=True))


def downgrade():
    # Check if tables exist
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    # Remove image_url from comment table
    if 'comment' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('comment')]
        if 'image_url' in columns:
            is_sqlite = bind.dialect.name == 'sqlite'
            if is_sqlite:
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.drop_column('image_url')
            else:
                op.drop_column('comment', 'image_url')
    
    # Remove image_url from post table
    if 'post' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('post')]
        if 'image_url' in columns:
            is_sqlite = bind.dialect.name == 'sqlite'
            if is_sqlite:
                with op.batch_alter_table('post', schema=None) as batch_op:
                    batch_op.drop_column('image_url')
            else:
                op.drop_column('post', 'image_url')
