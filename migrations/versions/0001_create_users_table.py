"""create users table

Revision ID: 0001
Revises:
Create Date: 2026-09-18

Matches the users row from the Day 1 ERD exactly: id (PK), email
(UNIQUE, NOT NULL), password_hash (NOT NULL), role (NOT NULL, one of
the brief's four roles). No columns invented beyond what's on paper.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

user_role_enum = PG_ENUM("pharmacist", "doctor", "manager", "supplier", name="userrole", create_type=False)


def upgrade() -> None:
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    user_role_enum.drop(op.get_bind(), checkfirst=True)
