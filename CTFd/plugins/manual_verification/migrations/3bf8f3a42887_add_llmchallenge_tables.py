"""Add LlmChallenge tables

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
            "llm_challenge",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("preprompt", sa.Text(), nullable=True),
            sa.Column("llm", sa.String(length=255), nullable=False),
            sa.ForeignKeyConstraint(["id"], ["challenges.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_table(
            "grt_submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("challenge_id", sa.Integer(), nullable=False),
            sa.Column("submission_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"]),
            sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_table(
            "grt_solves",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("challenge_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    except sa.exc.InternalError as e:
        print(str(e))


def downgrade(op=None):
    op.drop_table("llm_challenge")
