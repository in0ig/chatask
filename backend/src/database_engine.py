"""
数据库引擎配置

创建 SQLAlchemy 引擎和会话工厂，供整个项目使用。
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import logging

# 设置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入所有模型以确保它们被注册到Base.metadata中
# 必须在创建引擎之前导入所有模型
from src.models.base import Base
from src.models.data_source_model import DataSource
from src.models.data_preparation_model import DataTable, TableField, Dictionary, DictionaryItem, DynamicDictionaryConfig, TableRelation
from src.models.knowledge_base_model import KnowledgeBase
from src.models.knowledge_item_model import KnowledgeItem
from src.models.database_models import PromptConfig, SessionContext, ConversationMessage, TokenUsageStats
from src.models.fiscal_calendar_model import FiscalCalendar

# 从环境变量读取数据库配置
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '12345678')
DB_NAME = os.getenv('DB_NAME', 'chatbi')

# 检查是否处于测试模式
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'

# 验证所有模型都已正确注册到Base.metadata
# 打印所有已注册的表
registered_tables = sorted(list(Base.metadata.tables.keys()))
logger.info(f"Base.metadata.tables keys: {registered_tables}")

# 定义期望的表
expected_tables = [
    'data_sources', 'data_tables', 'table_fields', 'dictionaries', 
    'dictionary_items', 'dynamic_dictionary_configs', 'table_relations',
    'knowledge_bases', 'knowledge_items', 'prompt_config', 
    'session_context', 'conversation_messages', 'token_usage_stats',
    'fiscal_calendar'
]

# 验证所有期望的表都已注册
missing_tables = [table for table in expected_tables if table not in Base.metadata.tables]
if missing_tables:
    logger.error(f"以下表未注册到Base.metadata: {missing_tables}")
    logger.error(f"当前已注册的表: {registered_tables}")
    raise RuntimeError(f"以下表未注册到Base.metadata: {missing_tables}")

# 创建数据库引擎
if TEST_MODE:
    # 在测试模式下，使用SQLite文件数据库，确保连接共享
    # 创建临时文件作为SQLite数据库文件
    import tempfile
    TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_data_table.db")
    DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
    
    # 创建数据库引擎
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 验证表是否已创建
    created_tables = sorted(list(Base.metadata.tables.keys()))
    logger.info(f"Created tables: {created_tables}")
    
    # 使用这个引擎创建会话工厂
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
else:
    # 生产模式：使用MySQL数据库
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # 配置连接池参数
    POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))  # 连接池大小
    MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))  # 最大溢出连接数
    POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))  # 获取连接超时时间（秒）
    POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # 连接回收时间（秒）
    
    # 创建数据库引擎，配置连接池
    engine = create_engine(
        DATABASE_URL,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        pool_pre_ping=True,  # 在获取连接前检查连接是否有效
        echo=False,
        # 添加连接池监控
        pool_use_lifo=True,  # 使用LIFO策略，优先使用最近使用的连接
    )
    
    # 创建会话工厂
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        # 配置会话级超时
        expire_on_commit=False
    )
    
    # 使用 SQLAlchemy 事件系统注册连接池事件监听器
    from sqlalchemy import event
    
    # 监听连接创建事件
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        logger.debug(f"数据库连接创建: {id(dbapi_connection)}")
    
    # 监听连接释放事件
    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug(f"数据库连接释放: {id(dbapi_connection)}")
    
    # 监听连接检查失败事件
    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        # 注意：checkin 事件在连接返回池时触发，我们使用它来检测连接状态
        # 对于连接检查失败，我们依赖 pool_pre_ping 参数自动处理
        pass
    
    # 监听连接池错误事件
    @event.listens_for(engine, "first_connect")
    def on_first_connect(dbapi_connection, connection_record):
        # 这个事件在首次连接时触发，可用于初始化监控
        pass
    
    # 监听连接池错误事件
    @event.listens_for(engine, "engine_connect")
    def on_engine_connect(dbapi_connection, connection_record):
        # 这个事件在每次连接建立时触发
        pass

# 在模块级别定义连接池健康检查函数
def check_connection_pool_health():
    """检查连接池健康状态"""
    try:
        # 获取一个连接
        with engine.connect() as connection:
            # 执行简单的查询来验证连接
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                logger.info("数据库连接池健康检查通过")
                return True
            else:
                logger.error("数据库连接池健康检查失败: 查询返回异常值")
                return False
    except Exception as e:
        logger.error(f"数据库连接池健康检查失败: {str(e)}")
        return False

# 在模块级别定义连接池统计信息函数
def get_connection_pool_stats():
    """获取连接池统计信息"""
    try:
        stats = {
            'pool_size': engine.pool.size(),
            'pool_used': engine.pool.checkedout(),
            'pool_available': engine.pool.size() - engine.pool.checkedout(),
            'pool_overflow': engine.pool.overflow(),
            'pool_timeout': engine.pool.timeout(),
            'pool_recycle': engine.pool.recycle()
        }
        logger.debug(f"数据库连接池状态: {stats}")
        return stats
    except Exception as e:
        logger.error(f"获取连接池统计信息失败: {str(e)}")
        return None

# 在模块级别定义连接重试机制函数
def execute_with_retry(sql, max_retries=3):
    """带重试机制的SQL执行"""
    for attempt in range(max_retries):
        try:
            with engine.connect() as connection:
                result = connection.execute(text(sql))
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"SQL执行失败，已重试{max_retries}次: {str(e)}")
                raise
            logger.warning(f"SQL执行失败，第{attempt + 1}次重试: {str(e)}")
            # 等待一段时间后重试
            import time
            time.sleep(2 ** attempt)  # 指数退避

# 在应用启动时执行一次健康检查
if not check_connection_pool_health():
    logger.error("数据库连接池健康检查失败，应用可能无法正常启动")

# 统一导出所有需要的变量和函数
__all__ = ["engine", "SessionLocal", "check_connection_pool_health", "get_connection_pool_stats", "execute_with_retry"]