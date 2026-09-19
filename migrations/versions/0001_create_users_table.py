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

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# A native Postgres ENUM rather than a plain VARCHAR + CHECK: it's
# self-documenting in \d+ users, and asking for a role outside the four
# valid values fails at the database layer too, not just in Pydantic.
user_role = sa.Enum("pharmacist", "doctor", "manager", "supplier", name="userrole")


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    user_role.drop(op.get_bind(), checkfirst=True)
