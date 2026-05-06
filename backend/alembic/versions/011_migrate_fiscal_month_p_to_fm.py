"""migrate fiscal_month from P1..P12 to FM1..FM12

Revision ID: 011_migrate_fiscal_month_p_to_fm
Revises: 010_fiscal_calendar_multi_year
Create Date: 2026-04-20

数据修正：与 TimeResolver、导入约定及 fiscal_calendar_tools 的规范标签一致。
"""

from alembic import op

revision = "011_migrate_fiscal_month_p_to_fm"
down_revision = "010_fiscal_calendar_multi_year"
branch_labels = None
depends_on = None


def upgrade():
    # P10 -> FM10，P1 -> FM1
    op.execute(
        """
        UPDATE fiscal_calendar
        SET fiscal_month = CONCAT('FM', SUBSTRING(fiscal_month, 2))
        WHERE fiscal_month REGEXP '^P[0-9]{1,2}$'
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE fiscal_calendar
        SET fiscal_month = CONCAT('P', SUBSTRING(fiscal_month, 3))
        WHERE fiscal_month REGEXP '^FM[0-9]{1,2}$'
        """
    )
