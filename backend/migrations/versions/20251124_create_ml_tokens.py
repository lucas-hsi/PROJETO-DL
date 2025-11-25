from alembic import op
import sqlalchemy as sa


revision = "20251124_create_ml_tokens"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ml_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("expires_in", sa.Integer(), nullable=True),
        sa.Column("token_type", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("ml_tokens")