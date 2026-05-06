"""
数据准备模块模型
包含数据表、字段、字典、字典项、动态字典配置、表关联模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Integer, Text, JSON, ForeignKey
import sqlalchemy as sa
from sqlalchemy.orm import relationship
import uuid

from .base import Base


class DataTable(Base):
    """
    数据表配置模型
    支持 DIRECT_QUERY 和 IMPORT 两种数据模式
    """
    __tablename__ = 'data_tables'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='数据表ID（UUID）')
    data_source_id = Column(String(36), ForeignKey('data_sources.id'), nullable=False, index=True, comment='数据源ID')
    table_name = Column(String(100), nullable=False, index=True, comment='表名')
    display_name = Column(String(100), nullable=True, comment='显示名称')
    description = Column(Text(), nullable=True, comment='描述')
    data_mode = Column(Enum('DIRECT_QUERY', 'IMPORT'), nullable=False, index=True, comment='数据模式：DIRECT_QUERY或IMPORT')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    field_count = Column(Integer(), nullable=True, comment='字段数量')
    row_count = Column(Integer(), nullable=True, comment='行数')
    import_status = Column(Enum('PENDING', 'IN_PROGRESS', 'SUCCESS', 'FAILED'), nullable=True, comment='导入状态')
    last_sync_time = Column(DateTime(), nullable=True, comment='最后同步时间')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：属于一个数据源
    data_source = relationship('DataSource', back_populates='data_tables')
    # 关系：一个数据表可以有多个字段
    fields = relationship('TableField', back_populates='table', cascade='all, delete-orphan')
    # 关系：作为主表的关联
    primary_relations = relationship('TableRelation', foreign_keys='TableRelation.primary_table_id', back_populates='primary_table')
    # 关系：作为从表的关联
    foreign_relations = relationship('TableRelation', foreign_keys='TableRelation.foreign_table_id', back_populates='foreign_table')

    def __repr__(self):
        return f"<DataTable(id={self.id}, name='{self.table_name}', mode='{self.data_mode}', status={self.status})>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        def safe_isoformat(dt):
            """安全地转换datetime为ISO格式字符串"""
            if dt is None:
                return None
            if isinstance(dt, str):
                # 如果已经是字符串（如CURRENT_TIMESTAMP），跳过转换
                if dt in ['CURRENT_TIMESTAMP', 'CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP']:
                    return None
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        return {
            'id': self.id,
            'data_source_id': self.data_source_id,
            'table_name': self.table_name,
            'display_name': self.display_name,
            'description': self.description,
            'data_mode': self.data_mode,
            'status': self.status,
            'field_count': self.field_count,
            'row_count': self.row_count,
            'import_status': self.import_status,
            'last_sync_time': safe_isoformat(self.last_sync_time),
            'created_by': self.created_by,
            'created_at': safe_isoformat(self.created_at),
            'updated_at': safe_isoformat(self.updated_at)
        }


class TableField(Base):
    """
    表字段配置模型
    可选关联到字典表
    包含查询和聚合配置
    """
    __tablename__ = 'table_fields'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='字段ID（UUID）')
    table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, index=True, comment='数据表ID')
    field_name = Column(String(100), nullable=False, index=True, comment='字段名')
    display_name = Column(String(100), nullable=True, comment='显示名称')
    data_type = Column(String(50), nullable=False, comment='数据类型')
    description = Column(Text(), nullable=True, comment='描述')
    is_primary_key = Column(Boolean(), default=False, comment='是否为主键')
    is_nullable = Column(Boolean(), default=True, comment='是否允许为空')
    default_value = Column(String(255), nullable=True, comment='默认值')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=True, index=True, comment='字典ID')
    is_queryable = Column(Boolean(), default=True, index=True, comment='是否可查询')
    is_aggregatable = Column(Boolean(), default=True, index=True, comment='是否可聚合')
    sort_order = Column(Integer(), default=0, comment='排序顺序')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：属于一个数据表
    table = relationship('DataTable', back_populates='fields')
    # 关系：可能关联一个字典
    dictionary = relationship('Dictionary', back_populates='fields')
    # 关系：作为主表字段的关联
    primary_relations = relationship('TableRelation', foreign_keys='TableRelation.primary_field_id', back_populates='primary_field')
    # 关系：作为从表字段的关联
    foreign_relations = relationship('TableRelation', foreign_keys='TableRelation.foreign_field_id', back_populates='foreign_field')

    def __repr__(self):
        return f"<TableField(id={self.id}, name='{self.field_name}', table_id='{self.table_id}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'table_id': self.table_id,
            'field_name': self.field_name,
            'display_name': self.display_name,
            'data_type': self.data_type,
            'description': self.description,
            'is_primary_key': self.is_primary_key,
            'is_nullable': self.is_nullable,
            'default_value': self.default_value,
            'dictionary_id': self.dictionary_id,
            'is_queryable': self.is_queryable,
            'is_aggregatable': self.is_aggregatable,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Dictionary(Base):
    """
    字典表模型
    支持层级结构（parent_id）
    """
    __tablename__ = 'dictionaries'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='字典ID（UUID）')
    code = Column(String(50), nullable=False, unique=True, index=True, comment='字典编码')
    name = Column(String(100), nullable=False, comment='字典名称')
    parent_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=True, index=True, comment='父字典ID')
    description = Column(Text(), nullable=True, comment='描述')
    dict_type = Column(String(50), nullable=True, comment='字典类型')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    sort_order = Column(Integer(), default=0, comment='排序顺序')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：可以有子字典
    children = relationship('Dictionary', back_populates='parent', remote_side=[id])
    # 关系：父字典
    parent = relationship('Dictionary', back_populates='children', remote_side=[parent_id])
    # 关系：字典项
    items = relationship('DictionaryItem', back_populates='dictionary', cascade='all, delete-orphan')
    # 关系：字段引用
    fields = relationship('TableField', back_populates='dictionary')
    # 关系：动态字典配置
    dynamic_configs = relationship('DynamicDictionaryConfig', back_populates='dictionary', cascade='all, delete-orphan')
    # 关系：字典版本
    versions = relationship('DictionaryVersion', back_populates='dictionary', cascade='all, delete-orphan')
    # 关系：字典版本项
    version_items = relationship('DictionaryVersionItem', back_populates='dictionary', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Dictionary(id={self.id}, code='{self.code}', name='{self.name}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'parent_id': self.parent_id,
            'description': self.description,
            'dict_type': self.dict_type,
            'status': self.status,
            'sort_order': self.sort_order,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DictionaryItem(Base):
    """
    字典项模型
    关联到字典表
    包含键值对映射
    """
    __tablename__ = 'dictionary_items'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='字典项ID（UUID）')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=False, index=True, comment='字典ID')
    item_key = Column(String(100), nullable=False, index=True, comment='键值')
    item_value = Column(String(255), nullable=False, comment='值')
    description = Column(Text(), nullable=True, comment='描述')
    sort_order = Column(Integer(), default=0, comment='排序顺序')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    extra_data = Column(JSON(), nullable=True, comment='额外数据')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：属于一个字典
    dictionary = relationship('Dictionary', back_populates='items')

    def __repr__(self):
        return f"<DictionaryItem(id={self.id}, key='{self.item_key}', value='{self.item_value}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'dictionary_id': self.dictionary_id,
            'item_key': self.item_key,
            'item_value': self.item_value,
            'description': self.description,
            'sort_order': self.sort_order,
            'status': self.status,
            'extra_data': self.extra_data,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DynamicDictionaryConfig(Base):
    """
    动态字典配置模型
    关联到字典和数据源
    包含SQL查询配置
    """
    __tablename__ = 'dynamic_dictionary_configs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='动态字典配置ID（UUID）')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=False, index=True, comment='字典ID')
    data_source_id = Column(String(36), ForeignKey('data_sources.id'), nullable=False, index=True, comment='数据源ID')
    sql_query = Column(Text(), nullable=False, comment='SQL查询语句')
    key_field = Column(String(100), nullable=False, comment='键字段名')
    value_field = Column(String(100), nullable=False, comment='值字段名')
    refresh_interval = Column(Integer(), default=3600, comment='刷新间隔（秒）')
    last_refresh_time = Column(DateTime(), nullable=True, comment='最后刷新时间')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：属于一个字典
    dictionary = relationship('Dictionary', back_populates='dynamic_configs')
    # 关系：属于一个数据源
    data_source = relationship('DataSource', back_populates='dynamic_configs')

    def __repr__(self):
        return f"<DynamicDictionaryConfig(id={self.id}, dictionary_id='{self.dictionary_id}', data_source_id='{self.data_source_id}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'dictionary_id': self.dictionary_id,
            'data_source_id': self.data_source_id,
            'sql_query': self.sql_query,
            'key_field': self.key_field,
            'value_field': self.value_field,
            'refresh_interval': self.refresh_interval,
            'last_refresh_time': self.last_refresh_time.isoformat() if self.last_refresh_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class TableRelation(Base):
    """
    表关联模型
    关联主表和从表
    关联主表字段和从表字段
    支持 INNER、LEFT、RIGHT、FULL 四种 JOIN 类型
    """
    __tablename__ = 'table_relations'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='关联ID（UUID）')
    relation_name = Column(String(100), nullable=False, index=True, comment='关联名称')
    primary_table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, index=True, comment='主表ID')
    primary_field_id = Column(String(36), ForeignKey('table_fields.id'), nullable=False, comment='主表字段ID')
    foreign_table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, index=True, comment='外键表ID')
    foreign_field_id = Column(String(36), ForeignKey('table_fields.id'), nullable=False, comment='外键字段ID')
    join_type = Column(Enum('INNER', 'LEFT', 'RIGHT', 'FULL'), nullable=False, comment='连接类型')
    description = Column(Text(), nullable=True, comment='描述')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：主表
    primary_table = relationship('DataTable', foreign_keys=[primary_table_id], back_populates='primary_relations')
    # 关系：从表
    foreign_table = relationship('DataTable', foreign_keys=[foreign_table_id], back_populates='foreign_relations')
    # 关系：主表字段
    primary_field = relationship('TableField', foreign_keys=[primary_field_id], back_populates='primary_relations')
    # 关系：从表字段
    foreign_field = relationship('TableField', foreign_keys=[foreign_field_id], back_populates='foreign_relations')

    def __repr__(self):
        return f"<TableRelation(id={self.id}, name='{self.relation_name}', join_type='{self.join_type}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'relation_name': self.relation_name,
            'primary_table_id': self.primary_table_id,
            'primary_field_id': self.primary_field_id,
            'foreign_table_id': self.foreign_table_id,
            'foreign_field_id': self.foreign_field_id,
            'join_type': self.join_type,
            'description': self.description,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DictionaryVersion(Base):
    """
    字典版本模型
    存储字典的版本历史信息
    """
    __tablename__ = 'dictionary_versions'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='版本ID（UUID）')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=False, index=True, comment='字典ID')
    version_number = Column(Integer(), nullable=False, comment='版本号')
    version_name = Column(String(100), nullable=True, comment='版本名称')
    description = Column(Text(), nullable=True, comment='版本描述')
    change_type = Column(Enum('created', 'updated', 'deleted', 'restored', 'rollback'), nullable=False, comment='变更类型')
    change_summary = Column(Text(), nullable=True, comment='变更摘要')
    created_by = Column(String(100), nullable=False, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    is_current = Column(Boolean(), default=False, index=True, comment='是否为当前版本')
    items_count = Column(Integer(), default=0, comment='字典项数量')

    # 关系：属于一个字典
    dictionary = relationship('Dictionary', back_populates='versions')
    # 关系：版本中的字典项
    items = relationship('DictionaryVersionItem', back_populates='version', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<DictionaryVersion(id={self.id}, version_number={self.version_number}, dictionary_id='{self.dictionary_id}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'dictionary_id': self.dictionary_id,
            'version_number': self.version_number,
            'version_name': self.version_name,
            'description': self.description,
            'change_type': self.change_type,
            'change_summary': self.change_summary,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_current': self.is_current,
            'items_count': self.items_count
        }


class DictionaryVersionItem(Base):
    """
    字典版本项模型
    存储每个版本的字典项快照
    """
    __tablename__ = 'dictionary_version_items'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='版本项ID（UUID）')
    version_id = Column(String(36), ForeignKey('dictionary_versions.id'), nullable=False, index=True, comment='版本ID')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=False, index=True, comment='字典ID')
    item_key = Column(String(100), nullable=False, index=True, comment='键值')
    item_value = Column(String(255), nullable=False, comment='值')
    description = Column(Text(), nullable=True, comment='描述')
    sort_order = Column(Integer(), default=0, comment='排序顺序')
    status = Column(Boolean(), default=True, index=True, comment='是否启用')
    extra_data = Column(JSON(), nullable=True, comment='额外数据')
    change_type = Column(Enum('added', 'updated', 'deleted'), nullable=False, comment='变更类型')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')

    # 关系：属于一个版本
    version = relationship('DictionaryVersion', back_populates='items')
    # 关系：属于一个字典
    dictionary = relationship('Dictionary', back_populates='version_items')

    def __repr__(self):
        return f"<DictionaryVersionItem(id={self.id}, version_id='{self.version_id}', key='{self.item_key}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'version_id': self.version_id,
            'dictionary_id': self.dictionary_id,
            'item_key': self.item_key,
            'item_value': self.item_value,
            'description': self.description,
            'sort_order': self.sort_order,
            'status': self.status,
            'extra_data': self.extra_data,
            'change_type': self.change_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TableFolder(Base):
    """
    数据表文件夹模型
    支持层级结构（parent_id）
    """
    __tablename__ = 'table_folders'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='文件夹ID')
    name = Column(String(100), nullable=False, comment='文件夹名称')
    parent_id = Column(String(36), ForeignKey('table_folders.id'), nullable=True, comment='父文件夹ID，支持层级结构')
    description = Column(Text(), nullable=True, comment='文件夹描述')
    sort_order = Column(Integer(), default=0, comment='排序顺序')
    status = Column(Boolean(), default=True, comment='是否启用')
    created_by = Column(String(100), nullable=True, comment='创建人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：可以有子文件夹
    children = relationship('TableFolder', back_populates='parent', remote_side=[id])
    # 关系：父文件夹
    parent = relationship('TableFolder', back_populates='children', remote_side=[parent_id])
    # 关系：包含的数据表
    tables = relationship('DataTable', back_populates='folder', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<TableFolder(id={self.id}, name='{self.name}', parent_id='{self.parent_id}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        def safe_isoformat(dt):
            """安全地转换datetime为ISO格式字符串"""
            if dt is None:
                return None
            if isinstance(dt, str):
                # 如果已经是字符串（如CURRENT_TIMESTAMP），跳过转换
                if dt in ['CURRENT_TIMESTAMP', 'CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP']:
                    return None
                return dt
            if hasattr(dt, 'isoformat'):
                return dt.isoformat()
            return str(dt)
        
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'description': self.description,
            'sort_order': self.sort_order,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': safe_isoformat(self.created_at),
            'updated_at': safe_isoformat(self.updated_at)
        }


class DataTableSyncHistory(Base):
    """
    数据表同步历史记录模型
    用于跟踪表结构同步和数据导入的历史
    """
    __tablename__ = 'data_table_sync_history'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='同步历史ID（UUID）')
    table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, comment='数据表ID')
    sync_type = Column(Enum('STRUCTURE_SYNC', 'DATA_IMPORT', 'FIELD_UPDATE'), nullable=False, comment='同步类型')
    sync_status = Column(Enum('STARTED', 'IN_PROGRESS', 'SUCCESS', 'FAILED'), nullable=False, comment='同步状态')
    sync_message = Column(Text(), nullable=True, comment='同步消息')
    fields_added = Column(Integer(), default=0, comment='新增字段数')
    fields_updated = Column(Integer(), default=0, comment='更新字段数')
    fields_removed = Column(Integer(), default=0, comment='删除字段数')
    rows_imported = Column(Integer(), nullable=True, comment='导入行数')
    sync_duration = Column(Integer(), nullable=True, comment='同步耗时（秒）')
    created_by = Column(String(100), nullable=False, comment='操作人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    completed_at = Column(DateTime(), nullable=True, comment='完成时间')

    # 关系：属于一个数据表
    table = relationship('DataTable', back_populates='sync_history')

    def __repr__(self):
        return f"<DataTableSyncHistory(id={self.id}, table_id='{self.table_id}', sync_type='{self.sync_type}', status='{self.sync_status}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'table_id': self.table_id,
            'sync_type': self.sync_type,
            'sync_status': self.sync_status,
            'sync_message': self.sync_message,
            'fields_added': self.fields_added,
            'fields_updated': self.fields_updated,
            'fields_removed': self.fields_removed,
            'rows_imported': self.rows_imported,
            'sync_duration': self.sync_duration,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class TableFieldHistory(Base):
    """
    表字段变更历史记录模型
    用于跟踪字段级别的变更历史
    """
    __tablename__ = 'table_field_history'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='字段历史ID（UUID）')
    field_id = Column(String(36), ForeignKey('table_fields.id'), nullable=False, comment='字段ID')
    table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, comment='数据表ID')
    change_type = Column(Enum('CREATED', 'UPDATED', 'DELETED'), nullable=False, comment='变更类型')
    field_name = Column(String(100), nullable=False, comment='字段名')
    old_data_type = Column(String(50), nullable=True, comment='原数据类型')
    new_data_type = Column(String(50), nullable=True, comment='新数据类型')
    old_description = Column(Text(), nullable=True, comment='原描述')
    new_description = Column(Text(), nullable=True, comment='新描述')
    change_reason = Column(String(255), nullable=True, comment='变更原因')
    created_by = Column(String(100), nullable=False, comment='操作人')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')

    # 关系：属于一个字段
    field = relationship('TableField', back_populates='history')
    # 关系：属于一个数据表
    table = relationship('DataTable', back_populates='field_history')

    def __repr__(self):
        return f"<TableFieldHistory(id={self.id}, field_id='{self.field_id}', change_type='{self.change_type}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        return {
            'id': self.id,
            'field_id': self.field_id,
            'table_id': self.table_id,
            'change_type': self.change_type,
            'field_name': self.field_name,
            'old_data_type': self.old_data_type,
            'new_data_type': self.new_data_type,
            'old_description': self.old_description,
            'new_description': self.new_description,
            'change_reason': self.change_reason,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 修改 DataTable 模型，添加 folder_id 字段和 folder 关系，以及历史记录关系
DataTable.folder_id = Column(String(36), ForeignKey('table_folders.id'), nullable=True, comment='关联文件夹ID')
DataTable.folder = relationship('TableFolder', back_populates='tables')
DataTable.sync_history = relationship('DataTableSyncHistory', back_populates='table', cascade='all, delete-orphan')
DataTable.field_history = relationship('TableFieldHistory', back_populates='table', cascade='all, delete-orphan')

# 修改 TableField 模型，添加历史记录关系
TableField.history = relationship('TableFieldHistory', back_populates='field', cascade='all, delete-orphan')

class FieldMapping(Base):
    """
    字段映射模型
    用于建立数据表字段与数据字典的映射关系，提供业务语义
    """
    __tablename__ = 'field_mappings'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), comment='映射ID（UUID）')
    table_id = Column(String(36), ForeignKey('data_tables.id'), nullable=False, index=True, comment='数据表ID')
    field_id = Column(String(36), ForeignKey('table_fields.id'), nullable=False, index=True, comment='字段ID')
    dictionary_id = Column(String(36), ForeignKey('dictionaries.id'), nullable=True, index=True, comment='字典ID')
    business_name = Column(String(100), nullable=False, index=True, comment='业务名称')
    business_meaning = Column(Text(), nullable=True, comment='业务含义')
    value_range = Column(String(255), nullable=True, comment='取值范围')
    is_required = Column(Boolean(), default=False, comment='是否必填')
    default_value = Column(String(255), nullable=True, comment='默认值')
    created_at = Column(DateTime(), default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime(), default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关系：属于一个数据表
    table = relationship('DataTable', back_populates='field_mappings')
    # 关系：属于一个字段
    field = relationship('TableField', back_populates='field_mapping')
    # 关系：可能关联一个字典
    dictionary = relationship('Dictionary', back_populates='field_mappings')

    def __repr__(self):
        return f"<FieldMapping(id={self.id}, field_id='{self.field_id}', business_name='{self.business_name}')>"

    def to_dict(self):
        """转换为字典格式，便于序列化"""
        def safe_isoformat(dt):
            return dt.isoformat() if dt else None

        return {
            'id': self.id,
            'table_id': self.table_id,
            'field_id': self.field_id,
            'field_name': self.field.field_name if self.field else None,
            'field_type': self.field.data_type if self.field else None,
            'dictionary_id': self.dictionary_id,
            'dictionary_name': self.dictionary.name if self.dictionary else None,
            'business_name': self.business_name,
            'business_meaning': self.business_meaning,
            'value_range': self.value_range,
            'is_required': self.is_required,
            'default_value': self.default_value,
            'created_at': safe_isoformat(self.created_at),
            'updated_at': safe_isoformat(self.updated_at)
        }


# 添加关系到现有模型
DataTable.field_mappings = relationship('FieldMapping', back_populates='table', cascade='all, delete-orphan')
TableField.field_mapping = relationship('FieldMapping', back_populates='field', uselist=False, cascade='all, delete-orphan')
Dictionary.field_mappings = relationship('FieldMapping', back_populates='dictionary', cascade='all, delete-orphan')