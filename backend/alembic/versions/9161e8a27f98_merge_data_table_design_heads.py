"""merge data table design heads

Revision ID: 9161e8a27f98
Revises: 008_data_table_design_simplified, 7c0d4f8fc75e
Create Date: 2026-02-03 15:29:05.775137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9161e8a27f98'
down_revision: Union[str, Sequence[str], None] = ('008_data_table_design_simplified', '7c0d4f8fc75e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
