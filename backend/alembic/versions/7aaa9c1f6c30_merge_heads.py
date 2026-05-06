"""merge_heads

Revision ID: 7aaa9c1f6c30
Revises: 20260130182038_add_table_folders, 99e3899c81cd
Create Date: 2026-01-31 19:11:51.275311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7aaa9c1f6c30'
down_revision: Union[str, Sequence[str], None] = ('20260130182038_add_table_folders', '99e3899c81cd')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
