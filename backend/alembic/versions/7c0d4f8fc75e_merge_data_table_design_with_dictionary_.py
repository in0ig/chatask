"""merge data table design with dictionary updates

Revision ID: 7c0d4f8fc75e
Revises: 007_complete_data_table_design, bcef4db93c1d
Create Date: 2026-02-03 14:22:28.987446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c0d4f8fc75e'
down_revision: Union[str, Sequence[str], None] = ('007_complete_data_table_design', 'bcef4db93c1d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
