import logging
import os
import mysql.connector
from mysql.connector import pooling
from typing import Optional
from src.utils import logger

# 认证方式配置 - 仅支持密码认证，因为用户明确要求使用密码认证（DB_PASSWORD=12345678）
AUTH_METHODS = [
    {'method': 'password', 'description': '密码认证'}
]

# 不再支持 auth_socket 认证
AUTH_SOCKET_SUPPORTED = False

class DatabaseService:
    """
    数据库服务单例类，管理MySQL连接池
    使用单例模式确保整个应用中只有一个连接池实例
    """
    
    _instance = None
    _pool = None
    
    def __new__(cls):
        """单例模式：确保只有一个实例"""
        if cls._instance is None:
            cls._instance = super(DatabaseService, cls).__new__(cls)
        return cls._instance
    
    def initialize(self) -> bool:
        """
        初始化数据库连接池
        从环境变量读取数据库配置
        尝试多种认证方式以适应不同的MySQL配置
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 从环境变量读取配置
            db_config = {
                'host': os.getenv('DB_HOST'),
                'port': int(os.getenv('DB_PORT')),
                'user': os.getenv('DB_USER'),
                'database': os.getenv('DB_NAME'),
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci',
                'autocommit': True,
                'pool_name': 'chatbi_pool',
                'pool_size': int(os.getenv('DB_POOL_SIZE', '5')),  # 默认连接池大小为5
                'pool_reset_session': True
            }
            
            # 验证必要配置
            if not db_config['host']:
                raise ValueError("DB_HOST is required")
            if not db_config['user']:
                raise ValueError("DB_USER is required")
            if not db_config['database']:
                raise ValueError("DB_NAME is required")
            
            # 获取密码配置
            password = os.getenv('DB_PASSWORD', '')
            
            # 必须提供密码，因为仅支持密码认证
            if not password:
                raise ValueError("DB_PASSWORD 环境变量未设置。请确保已设置 DB_PASSWORD=12345678")
            
            # 创建配置副本并添加密码
            current_config = db_config.copy()
            current_config['password'] = password
            
            # 只有一种认证方式：password
            auth_method = AUTH_METHODS[0]
            
            logger.info(f"正在尝试使用 {auth_method['method']} 认证方式创建连接池...")
            try:
                self._pool = pooling.MySQLConnectionPool(**current_config)
                
                # 验证连接池是否创建成功
                if self._pool is None:
                    logger.error(f"{auth_method['method']} 认证方式下连接池创建失败，self._pool为None")
                    raise mysql.connector.Error("连接池创建失败，返回None")
                
                logger.info(f"使用 {auth_method['method']} 认证方式数据库连接池初始化成功")
                return True
                
            except mysql.connector.Error as e:
                logger.warning(f"{auth_method['method']} 认证方式失败: {str(e)}")
                # 由于没有其他认证方式，直接失败
                self._pool = None
                return False
            
            # 所有认证方式都失败了
            logger.error("所有认证方式都失败了，无法初始化数据库连接池")
            self._pool = None
            return False
        except ValueError as e:
            logger.error(f"数据库配置错误: {str(e)}")
            # 在初始化失败时重置连接池
            self._pool = None
            return False
        except Exception as e:
            logger.error(f"初始化数据库服务时发生未知错误: {str(e)}")
            # 在初始化失败时重置连接池
            self._pool = None
            return False
    
    def get_connection(self) -> Optional[mysql.connector.MySQLConnection]:
        """
        从连接池获取数据库连接
        
        Returns:
            mysql.connector.MySQLConnection: 数据库连接对象，失败时返回None
        """
        try:
            if self._pool is None:
                logger.warning("连接池未初始化，尝试自动初始化")
                if not self.initialize():
                    logger.error("自动初始化连接池失败。请检查：1) MySQL服务是否运行；2) DB_HOST、DB_USER、DB_NAME配置；3) 认证方式是否匹配（macOS可能需要auth_socket）")
                    return None
            
            connection = self._pool.get_connection()
            logger.debug("成功从连接池获取数据库连接")
            return connection
            
        except mysql.connector.Error as e:
            error_msg = str(e)
            if 'Access denied' in error_msg:
                logger.error(f"从连接池获取连接失败：认证失败。请检查用户名和密码，或尝试使用auth_socket认证方式。错误: {error_msg}")
            elif 'Unknown database' in error_msg:
                logger.error(f"从连接池获取连接失败：数据库不存在。请检查DB_NAME配置。错误: {error_msg}")
            elif 'Can\'t connect to' in error_msg:
                logger.error(f"从连接池获取连接失败：无法连接到MySQL服务器。请检查DB_HOST和DB_PORT配置，以及MySQL服务是否运行。错误: {error_msg}")
            else:
                logger.error(f"从连接池获取连接失败: {error_msg}")
            return None
        except Exception as e:
            logger.error(f"获取数据库连接时发生未知错误: {str(e)}")
            return None
    
    def health_check(self) -> dict:
        """
        检查数据库健康状态
        
        Returns:
            dict: 包含健康状态信息的字典
        """
        result = {
            'status': 'unknown',
            'connected': False,
            'pool_initialized': False,
            'database_name': 'N/A',
            'pool_size': 0,
            'active_connections': 0,
            'error': None
        }
        
        try:
            # 检查连接池是否初始化
            if self._pool is None:
                result['pool_initialized'] = False
                result['status'] = 'not_initialized'
                result['error'] = '连接池未初始化。请检查DB_HOST、DB_USER、DB_NAME配置，以及MySQL服务是否运行。对于macOS，可能需要使用auth_socket认证方式。'
                return result
            
            result['pool_initialized'] = True
            
            # 获取连接并执行简单查询检查数据库状态
            connection = self.get_connection()
            if connection is None:
                result['status'] = 'connection_failed'
                result['error'] = '无法获取数据库连接。请检查：1) MySQL服务是否运行；2) 用户名和密码是否正确；3) 数据库是否存在；4) 认证方式是否匹配（macOS可能需要auth_socket）'
                return result
            
            try:
                # 执行简单查询获取数据库名称
                cursor = connection.cursor()
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                cursor.close()
                
                result['database_name'] = db_name
                result['connected'] = True
                result['status'] = 'healthy'
                
                # 获取连接池统计信息
                result['pool_size'] = self._pool.pool_size
                # 由于MySQLConnectionPool没有_pool_counter属性，我们改为使用连接池大小作为活跃连接数的参考
                # 在健康检查中，active_connections应该为0，因为我们刚刚初始化了连接池
                # 实际活跃连接数无法准确获取，因此我们将其设置为0
                result['active_connections'] = 0
                
            except mysql.connector.Error as e:
                result['status'] = 'query_failed'
                if 'Access denied' in str(e):
                    result['error'] = f'数据库查询失败：认证失败。请检查用户名和密码，或尝试使用auth_socket认证方式。错误: {str(e)}'
                elif 'Unknown database' in str(e):
                    result['error'] = f'数据库查询失败：数据库不存在。请检查DB_NAME配置。错误: {str(e)}'
                else:
                    result['error'] = f"数据库查询失败: {str(e)}"
                logger.error(f"健康检查查询失败: {str(e)}")
            finally:
                # 确保连接被释放回池中
                if connection:
                    connection.close()
                    
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f"健康检查过程中发生未知错误: {str(e)}"
            logger.error(f"健康检查异常: {str(e)}")
            
        return result
    
    def close(self) -> bool:
        """
        关闭数据库连接池
        
        Returns:
            bool: 关闭是否成功
        """
        try:
            if self._pool is not None:
                self._pool._remove_connections()
                self._pool = None
                logger.info("数据库连接池已成功关闭")
                return True
            else:
                logger.info("连接池已关闭或未初始化")
                return True
                
        except Exception as e:
            logger.error(f"关闭连接池时发生错误: {str(e)}")
            return False
    
    def execute_query(self, query: str, params: tuple = ()) -> int:
        """
        执行SQL查询（INSERT, UPDATE, DELETE）
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        connection = None
        try:
            connection = self.get_connection()
            if connection is None:
                raise Exception("无法获取数据库连接")
            
            cursor = connection.cursor()
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            connection.commit()
            cursor.close()
            
            logger.debug(f"执行查询成功，影响 {affected_rows} 行")
            return affected_rows
            
        except mysql.connector.Error as e:
            logger.error(f"执行查询失败: {str(e)}")
            if connection:
                connection.rollback()
            raise
        finally:
            if connection:
                connection.close()
    
    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """
        执行SELECT查询并返回所有结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果列表
        """
        connection = None
        try:
            connection = self.get_connection()
            if connection is None:
                raise Exception("无法获取数据库连接")
            
            cursor = connection.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            
            logger.debug(f"查询成功，返回 {len(results)} 行")
            return results
            
        except mysql.connector.Error as e:
            logger.error(f"查询失败: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        """
        执行SELECT查询并返回单条结果
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            tuple: 查询结果，如果没有结果则返回None
        """
        connection = None
        try:
            connection = self.get_connection()
            if connection is None:
                raise Exception("无法获取数据库连接")
            
            cursor = connection.cursor()
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.close()
            
            logger.debug(f"查询成功，返回 {'1' if result else '0'} 行")
            return result
            
        except mysql.connector.Error as e:
            logger.error(f"查询失败: {str(e)}")
            raise
        finally:
            if connection:
                connection.close()

# 创建全局实例
# 这样可以在其他模块中直接导入和使用，无需手动实例化
database_service = DatabaseService()

# 确保通过DatabaseService()和database_service获取的是同一个实例
# 将database_service设置为类的实例
DatabaseService._instance = database_service