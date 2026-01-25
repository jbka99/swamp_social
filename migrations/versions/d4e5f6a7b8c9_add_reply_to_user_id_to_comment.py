"""add reply_to_user_id to comment

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-01-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # Check if 'comment' table exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' in existing_tables:
        # Check if column already exists
        columns = [col['name'] for col in inspector.get_columns('comment')]
        
        if 'reply_to_user_id' not in columns:
            # Detect database type
            is_sqlite = bind.dialect.name == 'sqlite'
            
            if is_sqlite:
                # Use batch mode for SQLite compatibility
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('reply_to_user_id', sa.Integer(), nullable=True))
                    batch_op.create_index('ix_comment_reply_to_user_id', ['reply_to_user_id'], unique=False)
            else:
                # For Postgres and other databases, add column and FK directly
                op.add_column('comment', 
                    sa.Column('reply_to_user_id', sa.Integer(), nullable=True)
                )
                op.create_foreign_key(
                    'fk_comment_reply_to_user_id',
                    'comment', 'user',
                    ['reply_to_user_id'], ['id']
                )
                op.create_index('ix_comment_reply_to_user_id', 'comment', ['reply_to_user_id'], unique=False)


def downgrade():
    # Check if 'comment' table exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' in existing_tables:
        # Check if column exists
        columns = [col['name'] for col in inspector.get_columns('comment')]
        
        if 'reply_to_user_id' in columns:
            # Detect database type
            is_sqlite = bind.dialect.name == 'sqlite'
            
            if is_sqlite:
                # Use batch mode for SQLite compatibility
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.drop_index('ix_comment_reply_to_user_id')
                    batch_op.drop_column('reply_to_user_id')
            else:
                # For Postgres and other databases
                op.drop_index('ix_comment_reply_to_user_id', table_name='comment')
                try:
                    op.drop_constraint('fk_comment_reply_to_user_id', 'comment', type_='foreignkey')
                except:
                    pass
                op.drop_column('comment', 'reply_to_user_id')
