"""merge knowledge base and items

Revision ID: 99e3899c81cd
Revises: 004, e02a290b0975
Create Date: 2026-01-21 15:08:40.321173

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99e3899c81cd'
down_revision: Union[str, Sequence[str], None] = ('004', 'e02a290b0975')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
