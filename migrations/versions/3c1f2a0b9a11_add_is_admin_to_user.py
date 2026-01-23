"""add is_admin to user

Revision ID: 3c1f2a0b9a11
Revises: 26d4a05e14cb
Create Date: 2026-01-24

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c1f2a0b9a11"
down_revision = "26d4a05e14cb"
branch_labels = None
depends_on = None


def upgrade():
    # Add column with a server default so existing rows get a value.
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # Remove the default after backfilling.
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column("is_admin", server_default=None)


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("is_admin")
