"""fiscal_calendar_multi_year_support

Revision ID: 010_fiscal_calendar_multi_year
Revises: 029bceb4ca13
Create Date: 2026-03-02

变更说明：
  - 去掉 fiscal_calendar.fw_label 的单列 unique 约束
  - 新增 (fiscal_year, fw_label) 联合唯一索引，支持多财年数据共存
"""

from alembic import op

revision = '010_fiscal_calendar_multi_year'
down_revision = '029bceb4ca13'
branch_labels = None
depends_on = None


def upgrade():
    # 删除旧的单列 unique 约束（MySQL 中 unique 约束以索引形式存在）
    # 约束名可能是 fw_label 或 uq_fw_label，用 try/except 兼容
    try:
        op.drop_index('fw_label', table_name='fiscal_calendar')
    except Exception:
        pass

    # 新增联合唯一索引
    op.create_index(
        'uq_fiscal_year_fw_label',
        'fiscal_calendar',
        ['fiscal_year', 'fw_label'],
        unique=True,
    )


def downgrade():
    op.drop_index('uq_fiscal_year_fw_label', table_name='fiscal_calendar')
    op.create_index('fw_label', 'fiscal_calendar', ['fw_label'], unique=True)
