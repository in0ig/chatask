"""merge_heads

Revision ID: 029bceb4ca13
Revises: 009_dialogue_sessions, 56aa2d976da9
Create Date: 2026-03-02 16:57:28.322083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '029bceb4ca13'
down_revision: Union[str, Sequence[str], None] = ('009_dialogue_sessions', '56aa2d976da9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
