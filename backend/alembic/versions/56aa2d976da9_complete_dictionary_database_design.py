"""complete dictionary database design

Revision ID: 56aa2d976da9
Revises: fc87d1a1a7a7
Create Date: 2026-02-04 01:11:58.821919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '56aa2d976da9'
down_revision: Union[str, Sequence[str], None] = 'fc87d1a1a7a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """完成数据字典数据库设计的升级操作"""
    
    # 1. 确保字段映射关系表存在（如果不存在则创建）
    # 这个表用于建立数据表字段与数据字典的映射关系
    try:
        op.create_table('field_mappings',
            sa.Column('id', sa.String(36), primary_key=True, comment='映射ID（UUID）'),
            sa.Column('table_id', sa.String(36), nullable=False, comment='数据表ID'),
            sa.Column('field_id', sa.String(36), nullable=False, comment='字段ID'),
            sa.Column('dictionary_id', sa.String(36), nullable=True, comment='字典ID'),
            sa.Column('business_name', sa.String(100), nullable=False, comment='业务名称'),
            sa.Column('business_meaning', sa.Text(), nullable=True, comment='业务含义'),
            sa.Column('value_range', sa.String(500), nullable=True, comment='取值范围'),
            sa.Column('is_required', sa.Boolean(), default=False, comment='是否必填'),
            sa.Column('default_value', sa.String(255), nullable=True, comment='默认值'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), comment='更新时间'),
            comment='字段映射关系表'
        )
        
        # 为字段映射表创建索引
        op.create_index('idx_field_mapping_table_id', 'field_mappings', ['table_id'])
        op.create_index('idx_field_mapping_field_id', 'field_mappings', ['field_id'])
        op.create_index('idx_field_mapping_dictionary_id', 'field_mappings', ['dictionary_id'])
        op.create_index('idx_field_mapping_business_name', 'field_mappings', ['business_name'])
        
        # 创建唯一约束，确保一个字段只能有一个映射
        op.create_unique_constraint('uq_field_mapping_field', 'field_mappings', ['field_id'])
        
    except Exception as e:
        # 如果表已存在，跳过创建
        print(f"字段映射表可能已存在: {e}")
    
    # 2. 为现有的字典相关表添加缺失的索引和约束（如果不存在）
    
    # 为字典表添加业务相关索引
    try:
        op.create_index('idx_dict_code_status', 'dictionaries', ['code', 'status'])
        op.create_index('idx_dict_type_status', 'dictionaries', ['dict_type', 'status'])
    except Exception:
        pass
    
    # 为字典项表添加业务相关索引
    try:
        op.create_index('idx_dict_item_value', 'dictionary_items', ['item_value'])
        op.create_index('idx_dict_item_sort', 'dictionary_items', ['dictionary_id', 'sort_order'])
    except Exception:
        pass
    
    # 3. 创建字典导入导出日志表
    try:
        op.create_table('dictionary_import_export_logs',
            sa.Column('id', sa.String(36), primary_key=True, comment='日志ID（UUID）'),
            sa.Column('dictionary_id', sa.String(36), nullable=False, comment='字典ID'),
            sa.Column('operation_type', sa.Enum('IMPORT', 'EXPORT'), nullable=False, comment='操作类型'),
            sa.Column('file_name', sa.String(255), nullable=True, comment='文件名'),
            sa.Column('file_format', sa.String(20), nullable=True, comment='文件格式'),
            sa.Column('status', sa.Enum('STARTED', 'SUCCESS', 'FAILED'), nullable=False, comment='操作状态'),
            sa.Column('total_items', sa.Integer(), default=0, comment='总项目数'),
            sa.Column('processed_items', sa.Integer(), default=0, comment='已处理项目数'),
            sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
            sa.Column('created_by', sa.String(100), nullable=False, comment='操作人'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), comment='创建时间'),
            sa.Column('completed_at', sa.DateTime(), nullable=True, comment='完成时间'),
            comment='字典导入导出日志表'
        )
        
        # 为导入导出日志表创建索引
        op.create_index('idx_import_export_dictionary_id', 'dictionary_import_export_logs', ['dictionary_id'])
        op.create_index('idx_import_export_operation_type', 'dictionary_import_export_logs', ['operation_type'])
        op.create_index('idx_import_export_status', 'dictionary_import_export_logs', ['status'])
        op.create_index('idx_import_export_created_at', 'dictionary_import_export_logs', ['created_at'])
        
    except Exception as e:
        print(f"字典导入导出日志表可能已存在: {e}")
    
    # 4. 添加数据完整性约束（使用原生SQL）
    
    # 确保字典编码的唯一性（在同一层级下）
    try:
        op.execute("""
            ALTER TABLE dictionaries 
            ADD CONSTRAINT uq_dict_code_parent 
            UNIQUE (code, parent_id)
        """)
    except Exception:
        pass
    
    # 确保字典项在同一字典下的键值唯一性
    try:
        op.execute("""
            ALTER TABLE dictionary_items 
            ADD CONSTRAINT uq_dict_item_key 
            UNIQUE (dictionary_id, item_key)
        """)
    except Exception:
        pass
    
    # 5. 创建视图以简化常用查询
    
    # 创建字段映射详情视图
    try:
        op.execute("""
            CREATE VIEW v_field_mapping_details AS
            SELECT 
                fm.id as mapping_id,
                fm.business_name,
                fm.business_meaning,
                fm.value_range,
                fm.is_required,
                fm.default_value,
                dt.id as table_id,
                dt.table_name,
                dt.display_name as table_display_name,
                tf.id as field_id,
                tf.field_name,
                tf.data_type,
                tf.description as field_description,
                d.id as dictionary_id,
                d.code as dictionary_code,
                d.name as dictionary_name,
                d.dict_type,
                fm.created_at,
                fm.updated_at
            FROM field_mappings fm
            LEFT JOIN data_tables dt ON fm.table_id = dt.id
            LEFT JOIN table_fields tf ON fm.field_id = tf.id
            LEFT JOIN dictionaries d ON fm.dictionary_id = d.id
            WHERE dt.status = TRUE AND tf.is_queryable = TRUE
        """)
    except Exception:
        pass
    
    # 创建字典层级结构视图
    try:
        op.execute("""
            CREATE VIEW v_dictionary_hierarchy AS
            WITH RECURSIVE dict_tree AS (
                -- 根节点
                SELECT 
                    id, code, name, parent_id, dict_type, status,
                    0 as level,
                    CAST(name AS CHAR(1000)) as path,
                    CAST(code AS CHAR(500)) as code_path
                FROM dictionaries 
                WHERE parent_id IS NULL AND status = TRUE
                
                UNION ALL
                
                -- 子节点
                SELECT 
                    d.id, d.code, d.name, d.parent_id, d.dict_type, d.status,
                    dt.level + 1,
                    CONCAT(dt.path, ' > ', d.name),
                    CONCAT(dt.code_path, '.', d.code)
                FROM dictionaries d
                INNER JOIN dict_tree dt ON d.parent_id = dt.id
                WHERE d.status = TRUE
            )
            SELECT * FROM dict_tree
            ORDER BY code_path
        """)
    except Exception:
        pass


def downgrade() -> None:
    """数据字典数据库设计的降级操作"""
    
    # 删除视图
    try:
        op.execute("DROP VIEW IF EXISTS v_dictionary_hierarchy")
        op.execute("DROP VIEW IF EXISTS v_field_mapping_details")
    except Exception:
        pass
    
    # 删除约束
    try:
        op.drop_constraint('uq_dict_item_key', 'dictionary_items', type_='unique')
        op.drop_constraint('uq_dict_code_parent', 'dictionaries', type_='unique')
    except Exception:
        pass
    
    # 删除导入导出日志表
    try:
        op.drop_table('dictionary_import_export_logs')
    except Exception:
        pass
    
    # 删除字段映射表
    try:
        op.drop_table('field_mappings')
    except Exception:
        pass
    
    # 删除添加的索引
    try:
        op.drop_index('idx_dict_item_sort', table_name='dictionary_items')
        op.drop_index('idx_dict_item_value', table_name='dictionary_items')
        op.drop_index('idx_dict_type_status', table_name='dictionaries')
        op.drop_index('idx_dict_code_status', table_name='dictionaries')
    except Exception:
        pass
