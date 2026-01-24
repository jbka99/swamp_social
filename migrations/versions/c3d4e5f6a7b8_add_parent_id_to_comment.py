"""add parent_id to comment table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-25 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Check if 'comment' table exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' in existing_tables:
        # Check if parent_id column already exists
        columns = [col['name'] for col in inspector.get_columns('comment')]
        
        if 'parent_id' not in columns:
            # Detect database type
            is_sqlite = bind.dialect.name == 'sqlite'
            
            if is_sqlite:
                # Use batch mode for SQLite compatibility
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
                    # SQLite doesn't support adding FK constraints via ALTER TABLE
                    # Foreign key will be enforced by SQLAlchemy relationships
                    batch_op.create_index('ix_comment_parent_id', ['parent_id'], unique=False)
            else:
                # For Postgres and other databases, add column and FK directly
                op.add_column('comment', sa.Column('parent_id', sa.Integer(), nullable=True))
                op.create_foreign_key(
                    'fk_comment_parent_id',
                    'comment', 'comment',
                    ['parent_id'], ['id'],
                    ondelete='CASCADE'
                )
                op.create_index('ix_comment_parent_id', 'comment', ['parent_id'], unique=False)


def downgrade():
    # Check if 'comment' table exists
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    if 'comment' in existing_tables:
        columns = [col['name'] for col in inspector.get_columns('comment')]
        
        if 'parent_id' in columns:
            # Detect database type
            is_sqlite = bind.dialect.name == 'sqlite'
            
            if is_sqlite:
                # Use batch mode for SQLite compatibility
                with op.batch_alter_table('comment', schema=None) as batch_op:
                    batch_op.drop_index('ix_comment_parent_id')
                    batch_op.drop_column('parent_id')
            else:
                # For Postgres and other databases
                op.drop_index('ix_comment_parent_id', table_name='comment')
                op.drop_constraint('fk_comment_parent_id', 'comment', type_='foreignkey')
                op.drop_column('comment', 'parent_id')
