"""
数据表服务层
处理数据表的增删改查操作
"""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from src.models.data_preparation_model import DataTable, TableField, TableRelation
from src.models.data_source_model import DataSource
from src.schemas.data_table_schema import DataTableCreate, DataTableUpdate, DataTableResponse, DataTableListResponse
from src.database import get_db

# 创建日志记录器
logger = logging.getLogger(__name__)

class DataTableService:
    """
    数据表服务类
    提供数据表的CRUD操作和相关业务逻辑
    """
    
    def __init__(self):
        pass
    
    def get_all_tables(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        source_id: Optional[str] = None,
        status: Optional[bool] = None
    ) -> DataTableListResponse:
        """
        获取数据表列表（支持分页、搜索、按数据源筛选）
        
        Args:
            db: 数据库会话
            page: 页码，从1开始
            page_size: 每页数量
            search: 搜索关键词（表名）
            source_id: 数据源ID，用于筛选
            status: 启用状态，用于筛选
            
        Returns:
            DataTableListResponse: 包含数据表列表和分页信息的响应对象
        """
        logger.info(f"Retrieving data tables with filters - page: {page}, page_size: {page_size}, search: {search}, source_id: {source_id}, status: {status}")
        
        # 构建查询条件，包含数据源信息
        query = db.query(DataTable).join(DataSource, DataTable.data_source_id == DataSource.id)
        
        # 按数据源ID筛选
        if source_id:
            query = query.filter(DataTable.data_source_id == source_id)
            
        # 按状态筛选
        if status is not None:
            query = query.filter(DataTable.status == status)
            
        # 按表名搜索
        if search:
            query = query.filter(DataTable.table_name.ilike(f"%{search}%"))
        
        # 应用排序
        query = query.order_by(DataTable.table_name)
        
        # 计算总数
        total = query.count()
        
        # 应用分页
        offset = (page - 1) * page_size
        tables = query.offset(offset).limit(page_size).all()
        
        # 转换为响应模型
        table_responses = []
        for table in tables:
            table_dict = table.to_dict()
            # 添加数据源名称
            if hasattr(table, 'data_source') and table.data_source:
                table_dict['data_source_name'] = table.data_source.name
            else:
                table_dict['data_source_name'] = '未知数据源'
            table_responses.append(DataTableResponse(**table_dict))
        
        logger.info(f"Retrieved {len(tables)} data tables out of {total} total")
        
        return DataTableListResponse(
            items=table_responses,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, (total + page_size - 1) // page_size)
        )
    
    def get_table_by_id(self, db: Session, table_id: str) -> Optional[DataTable]:
        """
        根据ID获取数据表详情
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            
        Returns:
            DataTable: 数据表对象，不存在时返回None
        """
        logger.info(f"Retrieving data table details for ID: {table_id}")
        
        return db.query(DataTable).filter(DataTable.id == table_id).first()
    
    def create_table(self, db: Session, table_data: DataTableCreate) -> DataTable:
        """
        创建数据表
        
        Args:
            db: 数据库会话
            table_data: 数据表创建数据
            
        Returns:
            DataTable: 创建的数据表对象
        """
        logger.info(f"Creating new data table: {table_data.table_name} for source {table_data.source_id}")
        
        # 验证数据源是否存在
        source = db.query(DataSource).filter(DataSource.id == table_data.source_id).first()
        if not source:
            raise ValueError(f"数据源不存在: {table_data.source_id}")
        
        # 获取当前时间
        now = datetime.now()
        
        # 创建数据表记录
        db_table = DataTable(
            data_source_id=table_data.source_id,
            table_name=table_data.table_name,
            display_name=table_data.table_name,
            description=table_data.description,
            data_mode='DIRECT_QUERY',
            row_count=table_data.row_count,
            field_count=table_data.column_count,
            status=table_data.status,
            created_by='test_user',
            created_at=now,
            updated_at=now
        )
        
        db.add(db_table)
        db.commit()
        db.refresh(db_table)
        
        logger.info(f"Data table created successfully: {table_data.table_name} (ID: {db_table.id})")
        
        return db_table
    
    def update_table(self, db: Session, table_id: str, table_data: DataTableUpdate) -> DataTable:
        """
        更新数据表
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            table_data: 数据表更新数据
            
        Returns:
            DataTable: 更新后的数据表对象
        """
        logger.info(f"Updating data table {table_id}")
        
        # 获取现有数据表
        db_table = self.get_table_by_id(db, table_id)
        if not db_table:
            raise ValueError(f"数据表不存在: {table_id}")
        
        # 更新字段
        for field, value in table_data.dict(exclude_unset=True).items():
            setattr(db_table, field, value)
        
        db.commit()
        db.refresh(db_table)
        
        logger.info(f"Data table {table_id} updated successfully")
        
        return db_table
    
    def delete_table(self, db: Session, table_id: str) -> bool:
        """
        删除数据表
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            
        Returns:
            bool: 删除是否成功
        """
        logger.info(f"Attempting to delete data table with ID: {table_id}")
        
        # 获取数据表
        db_table = self.get_table_by_id(db, table_id)
        if not db_table:
            logger.warning(f"Data table with ID {table_id} not found for deletion")
            return False
        
        # 删除数据表（级联删除字段）
        db.delete(db_table)
        db.commit()
        
        logger.info(f"Data table {table_id} deleted successfully")
        
        return True
    
    def has_related_columns(self, db: Session, table_id: str) -> bool:
        """
        检查数据表是否有关联的字段
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            
        Returns:
            bool: 是否有关联字段
        """
        count = db.query(TableField).filter(TableField.table_id == table_id).count()
        return count > 0

    def has_related_relations(self, db: Session, table_id: str) -> bool:
        """
        检查数据表是否有关联关系记录（主表或外键表）。

        Args:
            db: 数据库会话
            table_id: 数据表ID

        Returns:
            bool: 是否存在关联关系
        """
        count = db.query(TableRelation).filter(
            or_(
                TableRelation.primary_table_id == table_id,
                TableRelation.foreign_table_id == table_id,
            )
        ).count()
        return count > 0
    
    def get_table_columns(self, db: Session, table_id: str) -> List[TableField]:
        """
        获取数据表的所有字段（包含数据字典关系）
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            
        Returns:
            List[TableField]: 字段列表（预加载了 dictionary 关系）
        """
        from sqlalchemy.orm import joinedload
        
        # 使用 joinedload 预加载 dictionary 关系，避免 N+1 查询问题
        return db.query(TableField)\
            .options(joinedload(TableField.dictionary))\
            .filter(TableField.table_id == table_id)\
            .order_by(TableField.sort_order, TableField.field_name)\
            .all()
    
    def create_table_columns(self, db: Session, table_id: str, columns: List[dict]) -> List[TableField]:
        """
        创建数据表的字段
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            columns: 字段列表，每个元素是包含字段信息的字典
            
        Returns:
            List[TableField]: 创建的字段列表
        """
        created_columns = []
        
        for column_data in columns:
            db_column = TableField(
                table_id=table_id,
                field_name=column_data['name'],
                data_type=column_data.get('data_type'),
                is_primary_key=column_data.get('is_primary_key', False),
                is_nullable=column_data.get('is_nullable', True),
                description=column_data.get('description'),
                sort_order=column_data.get('sort_order', 0),
                is_queryable=column_data.get('is_queryable', True),
                is_aggregatable=column_data.get('is_aggregatable', True)
            )
            
            db.add(db_column)
            created_columns.append(db_column)
        
        db.commit()
        
        return created_columns
    
    def update_table_columns(self, db: Session, table_id: str, columns: List[dict]) -> List[TableField]:
        """
        更新数据表的字段
        
        Args:
            db: 数据库会话
            table_id: 数据表ID
            columns: 字段列表，每个元素是包含字段信息的字典
            
        Returns:
            List[TableField]: 更新后的字段列表
        """
        # 先删除现有字段
        db.query(TableField).filter(TableField.table_id == table_id).delete()
        
        # 再创建新字段
        return self.create_table_columns(db, table_id, columns)
    
    def get_tables_by_source(self, db: Session, source_id: str) -> List[DataTable]:
        """
        根据数据源ID获取所有数据表
        
        Args:
            db: 数据库会话
            source_id: 数据源ID
            
        Returns:
            List[DataTable]: 数据表列表
        """
        return db.query(DataTable).filter(DataTable.data_source_id == source_id).all()
    
    def get_table_by_name_and_source(self, db: Session, name: str, source_id: str) -> Optional[DataTable]:
        """
        根据表名和数据源ID获取数据表
        
        Args:
            db: 数据库会话
            name: 表名
            source_id: 数据源ID
            
        Returns:
            DataTable: 数据表对象，不存在时返回None
        """
        return db.query(DataTable).filter(
            and_(DataTable.table_name == name, DataTable.data_source_id == source_id)
        ).first()
