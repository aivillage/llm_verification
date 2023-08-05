"""Add LlmChallenge tables

Revision ID: 5510e0688fa2
Revises: 3bf8f3a42887
Create Date: 2020-05-08 15:11:03.647190

"""
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "5510e0688fa2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(op=None):
    op.create_table(
        "llm_challenge",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("preprompt", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["challenges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llm_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("anon_name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llmv_generation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("report", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["challenges.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["llm_models.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "llmv_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generation_id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["generation_id"], ["llmv_generation.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    

def downgrade(op=None):
    pass
