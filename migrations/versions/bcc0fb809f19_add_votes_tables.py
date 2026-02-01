"""add votes tables

Revision ID: bcc0fb809f19
Revises: 
Create Date: 2026-02-01 14:16:06.207594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bcc0fb809f19'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'post_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('value in (1, -1)', name='ck_post_vote_value'),
        sa.ForeignKeyConstraint(['post_id'], ['post.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'post_id', name='uq_post_votes_user_post'),
    )
    op.create_index('ix_post_votes_post_id', 'post_votes', ['post_id'], unique=False)
    op.create_index('ix_post_votes_user_id', 'post_votes', ['user_id'], unique=False)

    op.create_table(
        'comment_votes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.CheckConstraint('value in (1, -1)', name='ck_comment_vote_value'),
        sa.ForeignKeyConstraint(['comment_id'], ['comment.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'comment_id', name='uq_comment_votes_user_comment'),
    )
    op.create_index('ix_comment_votes_comment_id', 'comment_votes', ['comment_id'], unique=False)
    op.create_index('ix_comment_votes_user_id', 'comment_votes', ['user_id'], unique=False)


def downgrade():
    op.drop_index('ix_comment_votes_user_id', table_name='comment_votes')
    op.drop_index('ix_comment_votes_comment_id', table_name='comment_votes')
    op.drop_table('comment_votes')

    op.drop_index('ix_post_votes_user_id', table_name='post_votes')
    op.drop_index('ix_post_votes_post_id', table_name='post_votes')
    op.drop_table('post_votes')
