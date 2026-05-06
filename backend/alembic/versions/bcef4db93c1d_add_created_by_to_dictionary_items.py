"""add_created_by_to_dictionary_items

Revision ID: bcef4db93c1d
Revises: 567445871e5f
Create Date: 2026-02-01 21:41:15.272593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcef4db93c1d'
down_revision: Union[str, Sequence[str], None] = '567445871e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 添加 created_by 字段到 dictionary_items 表
    op.add_column('dictionary_items', 
                  sa.Column('created_by', sa.String(length=100), nullable=False, 
                           server_default='system', comment='创建人'))


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 created_by 字段
    op.drop_column('dictionary_items', 'created_by')
