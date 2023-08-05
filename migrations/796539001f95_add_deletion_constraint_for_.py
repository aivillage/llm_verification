"""Add deletion constraint for LlmChallenge

Revision ID: 796539001f95
Revises: 0d0f50cf3822
Create Date: 2020-05-08 15:23:09.953760

"""
# revision identifiers, used by Alembic.
revision = "796539001f95"
down_revision = "5510e0688fa2"
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
            "llmv_submissions_ibfk_1", "llmv_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_submissions_ibfk_2", "llmv_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_ibfk_1", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_ibfk_2", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_ibfk_3", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_ibfk_4", "llmv_generation", type_="foreignkey"
        )
    elif url.startswith("postgres"):
        op.drop_constraint(
            "llm_challenge_id_fkey", "llm_challenge", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_submissions_submission_id_fkey", "llmv_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_submissions_llmv_generation_fkey", "llmv_submissions", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_llm_challenge_fkey", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_users_fkey", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_teams_fkey", "llmv_generation", type_="foreignkey"
        )
        op.drop_constraint(
            "llmv_generation_teams_fkey", "llmv_generation", type_="foreignkey"
        )

    op.create_foreign_key(
        None, "llm_challenge", "challenges", ["id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_submissions", "submissions", ["submission_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_submissions", "llmv_generation", ["generation_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_generation", "llm_models", ["model_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_generation", "challenges", ["challenge_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_generation", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        None, "llmv_generation", "teams", ["team_id"], ["id"], ondelete="CASCADE"
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
