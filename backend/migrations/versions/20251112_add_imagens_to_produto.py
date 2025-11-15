"""
Add imagens JSONB column to produto table

Revision ID: 20251112_add_imagens
Revises: None
Create Date: 2025-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251112_add_imagens"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "produto",
        sa.Column("imagens", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("produto", "imagens")