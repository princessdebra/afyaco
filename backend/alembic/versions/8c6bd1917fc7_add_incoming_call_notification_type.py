"""add incoming_call notification type

Revision ID: 8c6bd1917fc7
Revises: e29546a77561
Create Date: 2026-10-28 11:13:19.016060

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c6bd1917fc7'
down_revision: Union[str, Sequence[str], None] = 'e29546a77561'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Not auto-detected by autogenerate — enum value additions never are.
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'INCOMING_CALL'")


def downgrade() -> None:
    """Downgrade schema."""
    # Postgres has no DROP VALUE for enums; not worth rebuilding the type
    # for a downgrade path that's unlikely to run.
    pass
