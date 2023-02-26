"""Add deletion constraint for LlmChallenge

Revision ID: 0d0f50cf3822
Revises: 1093835a1051
Create Date: 2020-05-08 15:23:09.953760

"""
# revision identifiers, used by Alembic.
revision = "0d0f50cf3822"
down_revision = "3bf8f3a42887"
branch_labels = None
depends_on = None


def upgrade(op=None):
    bind = op.get_bind()
    url = str(bind.engine.url)
    if url.startswith("mysql"):
        op.drop_constraint(
            "llm_challenge_ibfk_1", "llm_challenge", type_="foreignkey"
        )
        op.drop_constraint(
            "grt_submissions_ibfk_1", "grt_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "grt_submissions_ibfk_2", "grt_submissions", type_="foreignkey"
        )
    elif url.startswith("postgres"):
        op.drop_constraint(
            "llm_challenge_id_fkey", "llm_challenge", type_="foreignkey"
        )
        op.drop_constraint(
            "grt_submissions_challenge_id_fkey", "grt_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "grt_submissions_submission_id_fkey", "grt_submissions", type_="foreignkey"
        )

    op.create_foreign_key(
        None, "llm_challenge", "challenges", ["id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "grt_submissions", "challenges", ["challenge_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "grt_submissions", "submissions", ["submission_id"], ["id"], ondelete="CASCADE"
    )


def downgrade(op=None):
    bind = op.get_bind()
    url = str(bind.engine.url)
    if url.startswith("mysql"):
        op.drop_constraint(
            "llm_challenge_ibfk_1", "llm_challenge", type_="foreignkey"
        )
    elif url.startswith("postgres"):
        op.drop_constraint(
            "llm_challenge_id_fkey", "llm_challenge", type_="foreignkey"
        )

    op.create_foreign_key(
        "llm_challenge_ibfk_1", "llm_challenge", "challenges", ["id"], ["id"]
    )
