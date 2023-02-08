"""Add deletion constraint for ManualChallenge

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
            "manual_challenge_ibfk_1", "manual_challenge", type_="foreignkey"
        )
    elif url.startswith("postgres"):
        op.drop_constraint(
            "manual_challenge_id_fkey", "manual_challenge", type_="foreignkey"
        )

    op.create_foreign_key(
        None, "manual_challenge", "challenges", ["id"], ["id"], ondelete="CASCADE"
    )


def downgrade(op=None):
    bind = op.get_bind()
    url = str(bind.engine.url)
    if url.startswith("mysql"):
        op.drop_constraint(
            "manual_challenge_ibfk_1", "manual_challenge", type_="foreignkey"
        )
    elif url.startswith("postgres"):
        op.drop_constraint(
            "manual_challenge_id_fkey", "manual_challenge", type_="foreignkey"
        )

    op.create_foreign_key(
        "manual_challenge_ibfk_1", "manual_challenge", "challenges", ["id"], ["id"]
    )
