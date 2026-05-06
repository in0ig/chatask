"""add_dictionary_version_tables

Revision ID: 567445871e5f
Revises: 7aaa9c1f6c30
Create Date: 2026-01-31 19:12:15.463360

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '567445871e5f'
down_revision: Union[str, Sequence[str], None] = '7aaa9c1f6c30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 使用原生 SQL 创建 dictionary_versions 表，确保字符集兼容
    op.execute("""
        CREATE TABLE dictionary_versions (
            id VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '版本ID（UUID）',
            dictionary_id VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '字典ID',
            version_number INTEGER NOT NULL COMMENT '版本号',
            version_name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '版本名称',
            description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '版本描述',
            change_type ENUM('created', 'updated', 'deleted', 'restored', 'rollback') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '变更类型',
            change_summary TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '变更摘要',
            created_by VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '创建人',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            is_current BOOLEAN DEFAULT FALSE COMMENT '是否为当前版本',
            items_count INTEGER DEFAULT 0 COMMENT '字典项数量',
            PRIMARY KEY (id),
            FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id),
            INDEX idx_dictionary_id (dictionary_id),
            INDEX idx_version_number (version_number),
            INDEX idx_is_current (is_current)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='字典版本'
    """)
    
    # 使用原生 SQL 创建 dictionary_version_items 表
    op.execute("""
        CREATE TABLE dictionary_version_items (
            id VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '版本项ID（UUID）',
            version_id VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '版本ID',
            dictionary_id VARCHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '字典ID',
            item_key VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '键值',
            item_value VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '值',
            description TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '描述',
            sort_order INTEGER DEFAULT 0 COMMENT '排序顺序',
            status BOOLEAN DEFAULT TRUE COMMENT '是否启用',
            extra_data JSON COMMENT '额外数据',
            change_type ENUM('added', 'updated', 'deleted') CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '变更类型',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            PRIMARY KEY (id),
            FOREIGN KEY (version_id) REFERENCES dictionary_versions (id),
            FOREIGN KEY (dictionary_id) REFERENCES dictionaries (id),
            INDEX idx_version_id (version_id),
            INDEX idx_dictionary_id (dictionary_id),
            INDEX idx_item_key (item_key),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='字典版本项'
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 dictionary_version_items 表
    op.execute("DROP TABLE dictionary_version_items")
    
    # 删除 dictionary_versions 表
    op.execute("DROP TABLE dictionary_versions")
