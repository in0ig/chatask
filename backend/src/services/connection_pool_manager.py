"""
连接池管理服务

为ChatBI提供数据源连接池的统一管理，支持MySQL和SQL Server连接池。
包含连接池健康检查、统计信息监控和连接状态管理功能。
"""

import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import threading
from contextlib import contextmanager
from src.utils.sql_server_odbc import build_sql_server_connection_string

# 设置日志
logger = logging.getLogger(__name__)

class ConnectionPoolStatus(str, Enum):
    """连接池状态枚举"""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    INITIALIZING = "INITIALIZING"

@dataclass
class ConnectionPoolStats:
    """连接池统计信息"""
    pool_id: str
    db_type: str
    total_connections: int
    active_connections: int
    idle_connections: int
    failed_connections: int
    status: ConnectionPoolStatus
    last_check_time: float
    average_response_time: float
    error_rate: float

@dataclass
class ConnectionPoolConfig:
    """连接池配置"""
    pool_id: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    password: str
    domain: Optional[str] = None
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: int = 30
    idle_timeout: int = 300
    retry_attempts: int = 3
    health_check_interval: int = 60

class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self):
        self._pools: Dict[str, Any] = {}
        self._pool_stats: Dict[str, ConnectionPoolStats] = {}
        self._pool_configs: Dict[str, ConnectionPoolConfig] = {}
        self._lock = threading.RLock()
        self._monitoring_enabled = True
        logger.info("ConnectionPoolManager initialized")
    
    def create_pool(self, config: ConnectionPoolConfig) -> bool:
        """
        创建连接池
        
        Args:
            config: 连接池配置
            
        Returns:
            bool: 创建成功返回True
        """
        with self._lock:
            try:
                logger.info(f"Creating connection pool: {config.pool_id}")
                
                # 检查是否已存在
                if config.pool_id in self._pools:
                    logger.warning(f"Connection pool {config.pool_id} already exists")
                    return False
                
                # 根据数据库类型创建连接池
                if config.db_type.upper() == "MYSQL":
                    pool = self._create_mysql_pool(config)
                elif config.db_type.upper() == "SQL SERVER":
                    pool = self._create_sql_server_pool(config)
                else:
                    logger.error(f"Unsupported database type: {config.db_type}")
                    return False
                
                # 保存连接池和配置
                self._pools[config.pool_id] = pool
                self._pool_configs[config.pool_id] = config
                
                # 初始化统计信息
                self._pool_stats[config.pool_id] = ConnectionPoolStats(
                    pool_id=config.pool_id,
                    db_type=config.db_type,
                    total_connections=0,
                    active_connections=0,
                    idle_connections=0,
                    failed_connections=0,
                    status=ConnectionPoolStatus.INITIALIZING,
                    last_check_time=time.time(),
                    average_response_time=0.0,
                    error_rate=0.0
                )
                
                logger.info(f"Connection pool {config.pool_id} created successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create connection pool {config.pool_id}: {str(e)}")
                return False
    
    def _create_mysql_pool(self, config: ConnectionPoolConfig):
        """创建MySQL连接池"""
        try:
            import mysql.connector.pooling
            
            pool_config = {
                'pool_name': config.pool_id,
                'pool_size': config.max_connections,
                'pool_reset_session': True,
                'host': config.host,
                'port': config.port,
                'database': config.database_name,
                'user': config.username,
                'password': config.password,
                'connection_timeout': config.connection_timeout,
                'autocommit': True,
                'charset': 'utf8mb4',
                'use_unicode': True
            }
            
            pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"MySQL connection pool {config.pool_id} created")
            return pool
            
        except Exception as e:
            logger.error(f"Failed to create MySQL pool: {str(e)}")
            raise
    
    def _create_sql_server_pool(self, config: ConnectionPoolConfig):
        """创建SQL Server连接池"""
        try:
            # SQL Server连接池使用简单的连接管理
            # 实际生产环境可以使用更复杂的连接池实现
            pool_info = {
                'pool_id': config.pool_id,
                'config': config,
                'connections': [],
                'max_size': config.max_connections,
                'current_size': 0
            }
            
            logger.info(f"SQL Server connection pool {config.pool_id} created")
            return pool_info
            
        except Exception as e:
            logger.error(f"Failed to create SQL Server pool: {str(e)}")
            raise
    
    @contextmanager
    def get_connection(self, pool_id: str):
        """
        获取连接（上下文管理器）
        
        Args:
            pool_id: 连接池ID
            
        Yields:
            数据库连接对象
        """
        connection = None
        start_time = time.time()
        
        try:
            with self._lock:
                if pool_id not in self._pools:
                    raise ValueError(f"Connection pool {pool_id} not found")
                
                pool = self._pools[pool_id]
                config = self._pool_configs[pool_id]
                
                # 根据数据库类型获取连接
                if config.db_type.upper() == "MYSQL":
                    connection = pool.get_connection()
                elif config.db_type.upper() == "SQL SERVER":
                    connection = self._get_sql_server_connection(pool, config)
                
                # 更新统计信息
                self._update_connection_stats(pool_id, 'acquired', time.time() - start_time)
                
            yield connection
            
        except Exception as e:
            logger.error(f"Failed to get connection from pool {pool_id}: {str(e)}")
            self._update_connection_stats(pool_id, 'error', time.time() - start_time)
            raise
        finally:
            if connection:
                try:
                    # 根据数据库类型释放连接
                    config = self._pool_configs[pool_id]
                    if config.db_type.upper() == "MYSQL":
                        connection.close()  # MySQL连接池会自动回收
                    elif config.db_type.upper() == "SQL SERVER":
                        self._return_sql_server_connection(pool_id, connection)
                    
                    self._update_connection_stats(pool_id, 'released', time.time() - start_time)
                except Exception as e:
                    logger.error(f"Failed to release connection: {str(e)}")
    
    def _get_sql_server_connection(self, pool, config):
        """获取SQL Server连接"""
        try:
            import pyodbc
            
            # 构建连接字符串（支持可配置 SSL/TLS 参数）
            connection_string = build_sql_server_connection_string(
                host=config.host,
                port=config.port,
                database_name=config.database_name,
                username=config.username,
                password=config.password,
                domain=config.domain,
            )
            
            connection = pyodbc.connect(connection_string, timeout=config.connection_timeout)
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create SQL Server connection: {str(e)}")
            raise
    
    def _return_sql_server_connection(self, pool_id: str, connection):
        """归还SQL Server连接"""
        try:
            connection.close()
        except Exception as e:
            logger.error(f"Failed to close SQL Server connection: {str(e)}")
    
    def _update_connection_stats(self, pool_id: str, operation: str, response_time: float):
        """更新连接统计信息"""
        try:
            if pool_id in self._pool_stats:
                stats = self._pool_stats[pool_id]
                
                if operation == 'acquired':
                    stats.active_connections += 1
                elif operation == 'released':
                    stats.active_connections = max(0, stats.active_connections - 1)
                elif operation == 'error':
                    stats.failed_connections += 1
                
                # 更新平均响应时间
                if stats.average_response_time == 0:
                    stats.average_response_time = response_time
                else:
                    stats.average_response_time = (stats.average_response_time + response_time) / 2
                
                stats.last_check_time = time.time()
                
        except Exception as e:
            logger.error(f"Failed to update connection stats: {str(e)}")
    
    def check_pool_health(self, pool_id: str) -> bool:
        """
        检查连接池健康状态
        
        Args:
            pool_id: 连接池ID
            
        Returns:
            bool: 健康返回True
        """
        try:
            with self.get_connection(pool_id) as connection:
                # 执行简单查询测试连接
                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()
                
                if result and result[0] == 1:
                    self._pool_stats[pool_id].status = ConnectionPoolStatus.HEALTHY
                    logger.debug(f"Pool {pool_id} health check passed")
                    return True
                else:
                    self._pool_stats[pool_id].status = ConnectionPoolStatus.FAILED
                    logger.warning(f"Pool {pool_id} health check failed: invalid result")
                    return False
                    
        except Exception as e:
            logger.error(f"Pool {pool_id} health check failed: {str(e)}")
            if pool_id in self._pool_stats:
                self._pool_stats[pool_id].status = ConnectionPoolStatus.FAILED
            return False
    
    def get_pool_stats(self, pool_id: str) -> Optional[ConnectionPoolStats]:
        """
        获取连接池统计信息
        
        Args:
            pool_id: 连接池ID
            
        Returns:
            ConnectionPoolStats: 统计信息，不存在返回None
        """
        return self._pool_stats.get(pool_id)
    
    def get_all_pool_stats(self) -> Dict[str, ConnectionPoolStats]:
        """获取所有连接池统计信息"""
        return self._pool_stats.copy()
    
    def remove_pool(self, pool_id: str) -> bool:
        """
        移除连接池
        
        Args:
            pool_id: 连接池ID
            
        Returns:
            bool: 移除成功返回True
        """
        with self._lock:
            try:
                if pool_id not in self._pools:
                    logger.warning(f"Connection pool {pool_id} not found")
                    return False
                
                # 清理资源
                del self._pools[pool_id]
                del self._pool_configs[pool_id]
                del self._pool_stats[pool_id]
                
                logger.info(f"Connection pool {pool_id} removed")
                return True
                
            except Exception as e:
                logger.error(f"Failed to remove connection pool {pool_id}: {str(e)}")
                return False
    
    def start_monitoring(self):
        """启动连接池监控"""
        self._monitoring_enabled = True
        logger.info("Connection pool monitoring started")
    
    def stop_monitoring(self):
        """停止连接池监控"""
        self._monitoring_enabled = False
        logger.info("Connection pool monitoring stopped")

# 全局连接池管理器实例
connection_pool_manager = ConnectionPoolManager()