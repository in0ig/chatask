import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from src.models.data_source_model import DataSource
from src.models.data_preparation_model import DataTable  # 导入数据表模型用于关联检查
from src.services.connection_test import ConnectionTestService, ConnectionResult
from src.services.connection_pool_manager import (
    connection_pool_manager, 
    ConnectionPoolConfig, 
    ConnectionPoolStatus
)
from src.utils.encryption import decrypt_password
from datetime import datetime

# 创建日志记录器
logger = logging.getLogger(__name__)

class DataSourceService:
    def __init__(self):
        logger.info("DataSourceService initialized")
    
    def get_all_sources(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[bool] = None,
        db_type: Optional[str] = None,
        source_type: Optional[str] = None
    ) -> tuple[List[DataSource], int]:
        """
        获取数据源列表，支持分页、搜索、筛选
        
        Args:
            db: SQLAlchemy数据库会话
            page: 页码，从1开始
            page_size: 每页数量
            search: 搜索关键词（名称、描述）
            status: 启用状态
            db_type: 数据库类型
            source_type: 数据源类型
            
        Returns:
            tuple[List[DataSource], int]: (数据源列表, 总数量)
        """
        logger.info(f"Retrieving data sources with filters - page: {page}, page_size: {page_size}, search: {search}, status: {status}, db_type: {db_type}, source_type: {source_type}")
        
        query = db.query(DataSource)
        
        # 搜索功能：在名称和描述中搜索
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    DataSource.name.ilike(search_pattern),
                    DataSource.description.ilike(search_pattern)
                )
            )
        
        # 状态筛选
        if status is not None:
            query = query.filter(DataSource.status == status)
        
        # 数据库类型筛选
        if db_type:
            query = query.filter(DataSource.db_type == db_type)
        
        # 数据源类型筛选
        if source_type:
            query = query.filter(DataSource.source_type == source_type)
        
        # 获取总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * page_size
        sources = query.offset(offset).limit(page_size).all()
        
        logger.info(f"Retrieved {len(sources)} data sources")
        return sources, total

    def get_source_by_id(self, db: Session, source_id: str) -> Optional[DataSource]:
        """
        根据ID获取数据源
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            
        Returns:
            DataSource or None: 数据源对象，不存在时返回None
        """
        logger.info(f"Retrieving data source by ID: {source_id}")
        return db.query(DataSource).filter(DataSource.id == source_id).first()

    def add_data_source(self, db: Session, source: DataSource) -> DataSource:
        """
        添加新数据源
        
        Args:
            db: SQLAlchemy数据库会话
            source: DataSource对象
            
        Returns:
            DataSource: 添加后的数据源对象
        """
        logger.info(f"Adding new data source: name='{source.name}', type='{source.source_type}'")
        db.add(source)
        db.commit()
        db.refresh(source)
        
        # 创建连接池（如果是数据库类型）
        if source.source_type == "DATABASE" and source.status:
            self._create_connection_pool(source)
        
        logger.info(f"Data source added successfully: {source.name} (ID: {source.id})")
        return source

    def update_data_source(self, db: Session, source_id: str, update_data: dict) -> Optional[DataSource]:
        """
        更新数据源
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            update_data: 要更新的字段字典
            
        Returns:
            DataSource or None: 更新后的数据源对象，不存在时返回None
        """
        logger.info(f"Updating data source {source_id} with data: {update_data}")
        
        source = self.get_source_by_id(db, source_id)
        if not source:
            return None
        
        # 记录原始状态
        old_status = source.status
        
        # 更新字段
        for field, value in update_data.items():
            if hasattr(source, field):
                setattr(source, field, value)
        
        db.commit()
        db.refresh(source)
        
        # 处理连接池状态变化
        if source.source_type == "DATABASE":
            if not old_status and source.status:
                # 从禁用变为启用，创建连接池
                self._create_connection_pool(source)
            elif old_status and not source.status:
                # 从启用变为禁用，移除连接池
                self._remove_connection_pool(source_id)
            elif source.status:
                # 仍然启用，重新创建连接池（配置可能已更改）
                self._remove_connection_pool(source_id)
                self._create_connection_pool(source)
        
        logger.info(f"Data source {source_id} updated successfully")
        return source

    def delete_source(self, db: Session, source_id: str) -> bool:
        """
        删除数据源
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        logger.info(f"Attempting to delete data source with ID: {source_id}")
        
        source = self.get_source_by_id(db, source_id)
        if not source:
            logger.warning(f"Data source with ID {source_id} not found for deletion")
            return False
        
        # 移除连接池
        if source.source_type == "DATABASE":
            self._remove_connection_pool(source_id)
        
        db.delete(source)
        db.commit()
        logger.info(f"Data source {source_id} deleted successfully")
        return True

    def has_related_tables(self, db: Session, source_id: str) -> bool:
        """
        检查数据源是否有关联的数据表
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            
        Returns:
            bool: 有关联数据表返回True，否则返回False
        """
        logger.info(f"Checking if data source {source_id} has related tables")
        
        # 检查是否有关联的数据表
        related_tables = db.query(DataTable).filter(DataTable.data_source_id == source_id).first()
        
        has_related = related_tables is not None
        logger.info(f"Data source {source_id} has related tables: {has_related}")
        return has_related

    def activate_source(self, db: Session, source_id: str) -> bool:
        """
        激活指定ID的数据源（兼容性方法）
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            
        Returns:
            bool: 激活成功返回True，失败返回False
        """
        logger.info(f"Attempting to activate data source with ID: {source_id}")
        
        source = self.get_source_by_id(db, source_id)
        if not source:
            logger.warning(f"Data source with ID {source_id} not found for activation")
            return False
        
        source.status = True
        db.commit()
        db.refresh(source)
        logger.info(f"Data source {source_id} activated successfully")
        return True

    def deactivate_source(self, db: Session, source_id: str) -> bool:
        """
        禁用指定ID的数据源（兼容性方法）
        
        Args:
            db: SQLAlchemy数据库会话
            source_id: 数据源ID
            
        Returns:
            bool: 禁用成功返回True，失败返回False
        """
        logger.info(f"Attempting to deactivate data source with ID: {source_id}")
        
        source = self.get_source_by_id(db, source_id)
        if not source:
            logger.warning(f"Data source with ID {source_id} not found for deactivation")
            return False
        
        source.status = False
        db.commit()
        db.refresh(source)
        logger.info(f"Data source {source_id} deactivated successfully")
        return True
    
    def test_connection(self, data_source: DataSource) -> dict:
        """
        测试数据源连接
        
        Args:
            data_source: DataSource对象
            
        Returns:
            dict: 包含连接结果和延迟信息的字典
        """
        logger.info(f"Testing connection for data source {data_source.id}")
        
        # 创建测试数据字典
        test_data = {
            "name": data_source.name,
            "source_type": data_source.source_type,
            "db_type": data_source.db_type,
            "host": data_source.host,
            "port": data_source.port,
            "database_name": data_source.database_name,
            "auth_type": data_source.auth_type,
            "username": data_source.username,
            "password": data_source.password,
            "domain": data_source.domain
        }
        
        # 使用连接测试服务进行测试
        result = ConnectionTestService.test_connection(test_data)
        
        # 更新数据源的连接状态
        if result.success:
            data_source.connection_status = "CONNECTED"
            data_source.last_test_time = datetime.now()
        else:
            data_source.connection_status = "FAILED"
            data_source.last_test_time = datetime.now()
        
        # 保存更新后的连接状态
        from src.database import get_db
        db_session = next(get_db())
        db_session.commit()
        
        # 转换为字典格式返回
        return {
            "success": result.success,
            "error": result.message,
            "connection_status": "CONNECTED" if result.success else "FAILED",
            "elapsed_time_ms": result.latency_ms,
            "details": result.message
        }
    
    def _create_connection_pool(self, source: DataSource) -> bool:
        """
        为数据源创建连接池
        
        Args:
            source: DataSource对象
            
        Returns:
            bool: 创建成功返回True
        """
        try:
            # 解密密码
            decrypted_password = None
            if source.password:
                decrypted_password = decrypt_password(source.password)
            
            # 创建连接池配置
            config = ConnectionPoolConfig(
                pool_id=source.id,
                db_type=source.db_type,
                host=source.host,
                port=source.port,
                database_name=source.database_name,
                username=source.username,
                password=decrypted_password,
                domain=source.domain,
                min_connections=5,
                max_connections=20,
                connection_timeout=30,
                idle_timeout=300
            )
            
            # 创建连接池
            success = connection_pool_manager.create_pool(config)
            if success:
                logger.info(f"Connection pool created for data source {source.id}")
            else:
                logger.warning(f"Failed to create connection pool for data source {source.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating connection pool for data source {source.id}: {str(e)}")
            return False
    
    def _remove_connection_pool(self, source_id: str) -> bool:
        """
        移除数据源的连接池
        
        Args:
            source_id: 数据源ID
            
        Returns:
            bool: 移除成功返回True
        """
        try:
            success = connection_pool_manager.remove_pool(source_id)
            if success:
                logger.info(f"Connection pool removed for data source {source_id}")
            else:
                logger.warning(f"Connection pool not found for data source {source_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error removing connection pool for data source {source_id}: {str(e)}")
            return False
    
    def get_connection_pool_stats(self, source_id: str) -> Optional[dict]:
        """
        获取数据源连接池统计信息
        
        Args:
            source_id: 数据源ID
            
        Returns:
            dict: 连接池统计信息，不存在返回None
        """
        try:
            stats = connection_pool_manager.get_pool_stats(source_id)
            if stats:
                return {
                    "pool_id": stats.pool_id,
                    "db_type": stats.db_type,
                    "total_connections": stats.total_connections,
                    "active_connections": stats.active_connections,
                    "idle_connections": stats.idle_connections,
                    "failed_connections": stats.failed_connections,
                    "status": stats.status.value,
                    "last_check_time": stats.last_check_time,
                    "average_response_time": stats.average_response_time,
                    "error_rate": stats.error_rate
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting connection pool stats for {source_id}: {str(e)}")
            return None
    
    def check_connection_pool_health(self, source_id: str) -> bool:
        """
        检查数据源连接池健康状态
        
        Args:
            source_id: 数据源ID
            
        Returns:
            bool: 健康返回True
        """
        try:
            return connection_pool_manager.check_pool_health(source_id)
        except Exception as e:
            logger.error(f"Error checking connection pool health for {source_id}: {str(e)}")
            return False