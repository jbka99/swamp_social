"""add comment table

Revision ID: b2c3d4e5f6a7
Revises: 573fca43d9e7
Create Date: 2026-01-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = '573fca43d9e7'
branch_labels = None
depends_on = None


def upgrade():
    # Check if 'comment' table already exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' not in existing_tables:
        # Create comment table only if it doesn't exist
        op.create_table('comment',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('date_posted', sa.DateTime(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('post_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        # Add indexes for better query performance
        op.create_index('ix_comment_post_id', 'comment', ['post_id'], unique=False)
        op.create_index('ix_comment_user_id', 'comment', ['user_id'], unique=False)


def downgrade():
    # Check if 'comment' table exists before dropping
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' in existing_tables:
        # Drop indexes first
        op.drop_index('ix_comment_user_id', table_name='comment')
        op.drop_index('ix_comment_post_id', table_name='comment')
        # Then drop the table
        op.drop_table('comment')
