"""Add ManualChallenge table

Revision ID: 3bf8f3a42887
Revises: 1093835a1051
Create Date: 2020-05-08 15:11:03.647190

"""
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "3bf8f3a42887"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    try:
        op.create_table(
            "manual_challenge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["id"], ["challenges.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    except sa.exc.InternalError as e:
        print(str(e))


def downgrade(op=None):
    op.drop_table("manual_challenge")
