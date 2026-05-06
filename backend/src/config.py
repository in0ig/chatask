"""
配置管理模块
使用 Pydantic 进行配置验证和管理
从 .env 文件加载环境变量
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
import logging

# 加载 .env 文件
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """数据库配置模型"""
    host: str = Field(default="127.0.0.1", description="数据库主机地址")
    port: int = Field(default=3306, description="数据库端口")
    user: str = Field(default="root", description="数据库用户名")
    password: str = Field(default="", description="数据库密码")
    database: str = Field(default="chatbi", description="数据库名称")
    pool_size: int = Field(default=5, description="连接池大小")
    
    @validator('port')
    def validate_port(cls, v):
        """验证端口号范围"""
        if not 1 <= v <= 65535:
            raise ValueError(f"端口号必须在 1-65535 之间，当前值: {v}")
        return v
    
    @validator('pool_size')
    def validate_pool_size(cls, v):
        """验证连接池大小"""
        if not 1 <= v <= 100:
            raise ValueError(f"连接池大小必须在 1-100 之间，当前值: {v}")
        return v
    
    class Config:
        """Pydantic 配置"""
        validate_assignment = True

class RedisConfig(BaseModel):
    """Redis配置模型"""
    host: str = Field(default="127.0.0.1", description="Redis主机地址")
    port: int = Field(default=6379, description="Redis端口")
    db: int = Field(default=0, description="Redis数据库编号")
    password: str = Field(default="", description="Redis密码")
    cache_enabled: bool = Field(default=True, description="字典缓存是否启用")
    cache_ttl: int = Field(default=3600, description="字典缓存过期时间（秒）")
    
    @validator('port')
    def validate_port(cls, v):
        """验证端口号范围"""
        if not 1 <= v <= 65535:
            raise ValueError(f"端口号必须在 1-65535 之间，当前值: {v}")
        return v
    
    @validator('db')
    def validate_db(cls, v):
        """验证数据库编号范围"""
        if not 0 <= v <= 15:
            raise ValueError(f"Redis数据库编号必须在 0-15 之间，当前值: {v}")
        return v
    
    @validator('cache_ttl')
    def validate_cache_ttl(cls, v):
        """验证缓存过期时间"""
        if v < 0:
            raise ValueError(f"缓存过期时间不能为负数，当前值: {v}")
        return v
    
    class Config:
        """Pydantic 配置"""
        validate_assignment = True
    

class AppConfig(BaseModel):
    """应用配置模型"""
    database: DatabaseConfig
    redis: RedisConfig
    model_type: str = Field(default="local", description="模型类型: local 或 cloud")
    qwen_model_name: str = Field(default="qwen-agent", description="Qwen 模型名称")
    qwen_api_key: Optional[str] = Field(default=None, description="Qwen API 密钥")
    log_level: str = Field(default="INFO", description="日志级别")
    debug: bool = Field(default=False, description="调试模式")
    enable_streaming: bool = Field(default=True, description="启用流式输出")
    streaming_timeout: int = Field(default=60, description="流式调用超时时间（秒）")
    retrieval_normal_max_terms: int = Field(default=30, description="normal召回术语上限")
    retrieval_normal_max_logics: int = Field(default=20, description="normal召回逻辑上限")
    retrieval_normal_max_events: int = Field(default=10, description="normal召回事项上限")
    retrieval_normal_table_keep: int = Field(default=30, description="normal保留表级知识上限")
    retrieval_normal_global_keep: int = Field(default=10, description="normal保留全局知识上限")
    retrieval_normal_dictionary_keep: int = Field(default=30, description="normal保留字典上限")
    retrieval_expanded_max_terms: int = Field(default=80, description="expanded召回术语上限")
    retrieval_expanded_max_logics: int = Field(default=50, description="expanded召回逻辑上限")
    retrieval_expanded_max_events: int = Field(default=20, description="expanded召回事项上限")
    retrieval_expanded_table_keep: int = Field(default=60, description="expanded保留表级知识上限")
    retrieval_expanded_global_keep: int = Field(default=20, description="expanded保留全局知识上限")
    retrieval_expanded_dictionary_keep: int = Field(default=60, description="expanded保留字典上限")
    
    @validator('streaming_timeout')
    def validate_streaming_timeout(cls, v):
        """验证流式调用超时时间"""
        if v < 10 or v > 300:
            raise ValueError(f"流式调用超时时间必须在 10-300 秒之间，当前值: {v}")
        return v

    @validator(
        'retrieval_normal_max_terms',
        'retrieval_normal_max_logics',
        'retrieval_normal_max_events',
        'retrieval_normal_table_keep',
        'retrieval_normal_global_keep',
        'retrieval_normal_dictionary_keep',
        'retrieval_expanded_max_terms',
        'retrieval_expanded_max_logics',
        'retrieval_expanded_max_events',
        'retrieval_expanded_table_keep',
        'retrieval_expanded_global_keep',
        'retrieval_expanded_dictionary_keep',
    )
    def validate_positive_retrieval_limits(cls, v):
        """验证召回相关阈值必须为正整数"""
        if v < 1:
            raise ValueError(f"召回阈值必须 >= 1，当前值: {v}")
        return v
    
    @validator('model_type')
    def validate_model_type(cls, v):
        """验证模型类型"""
        allowed_types = ['local', 'cloud']
        if v not in allowed_types:
            raise ValueError(f"模型类型必须是 {allowed_types} 之一，当前值: {v}")
        return v
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """验证日志级别"""
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(f"日志级别必须是 {allowed_levels} 之一，当前值: {v}")
        return v_upper
    
    @validator('qwen_api_key')
    def validate_api_key(cls, v, values):
        """验证 API 密钥（仅在 cloud 模式下需要）"""
        if values.get('model_type') == 'cloud' and not v:
            raise ValueError("使用 cloud 模式时必须提供 QWEN_API_KEY")
        return v
    
    class Config:
        """Pydantic 配置"""
        validate_assignment = True





def load_config() -> AppConfig:
    """
    从环境变量加载配置
    
    Returns:
        AppConfig: 应用配置对象
        
    Raises:
        ValueError: 配置验证失败时抛出
    """
    try:
        # 加载数据库配置
        db_config = DatabaseConfig(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'chatbi'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '5'))
        )
        
        # 加载Redis配置
        redis_config = RedisConfig(
            host=os.getenv('REDIS_HOST', '127.0.0.1'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD', ''),
            cache_enabled=os.getenv('DICTIONARY_CACHE_ENABLED', 'true').lower() in ('true', '1', 'yes'),
            cache_ttl=int(os.getenv('DICTIONARY_CACHE_TTL', '3600'))
        )
        
        # 加载应用配置
        app_config = AppConfig(
            database=db_config,
            redis=redis_config,
            model_type=os.getenv('MODEL_TYPE', 'local'),
            qwen_model_name=os.getenv('QWEN_MODEL_NAME', 'qwen-agent'),
            qwen_api_key=os.getenv('QWEN_API_KEY'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            debug=os.getenv('DEBUG', 'false').lower() in ('true', '1', 'yes'),
            enable_streaming=os.getenv('ENABLE_STREAMING', 'true').lower() in ('true', '1', 'yes'),
            streaming_timeout=int(os.getenv('STREAMING_TIMEOUT', '60')),
            retrieval_normal_max_terms=int(os.getenv('RETRIEVAL_NORMAL_MAX_TERMS', '30')),
            retrieval_normal_max_logics=int(os.getenv('RETRIEVAL_NORMAL_MAX_LOGICS', '20')),
            retrieval_normal_max_events=int(os.getenv('RETRIEVAL_NORMAL_MAX_EVENTS', '10')),
            retrieval_normal_table_keep=int(os.getenv('RETRIEVAL_NORMAL_TABLE_KEEP', '30')),
            retrieval_normal_global_keep=int(os.getenv('RETRIEVAL_NORMAL_GLOBAL_KEEP', '10')),
            retrieval_normal_dictionary_keep=int(os.getenv('RETRIEVAL_NORMAL_DICTIONARY_KEEP', '30')),
            retrieval_expanded_max_terms=int(os.getenv('RETRIEVAL_EXPANDED_MAX_TERMS', '80')),
            retrieval_expanded_max_logics=int(os.getenv('RETRIEVAL_EXPANDED_MAX_LOGICS', '50')),
            retrieval_expanded_max_events=int(os.getenv('RETRIEVAL_EXPANDED_MAX_EVENTS', '20')),
            retrieval_expanded_table_keep=int(os.getenv('RETRIEVAL_EXPANDED_TABLE_KEEP', '60')),
            retrieval_expanded_global_keep=int(os.getenv('RETRIEVAL_EXPANDED_GLOBAL_KEEP', '20')),
            retrieval_expanded_dictionary_keep=int(os.getenv('RETRIEVAL_EXPANDED_DICTIONARY_KEEP', '60')),
        )
        
        logger.info("配置加载成功")
        return app_config
        
    except ValueError as e:
        logger.error(f"配置验证失败: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"加载配置时发生错误: {str(e)}")
        raise ValueError(f"配置加载失败: {str(e)}")


def validate_config(config: AppConfig) -> tuple[bool, list[str]]:
    """
    验证配置的完整性和正确性
    
    Args:
        config: 应用配置对象
        
    Returns:
        tuple[bool, list[str]]: (是否有效, 错误消息列表)
    """
    errors = []
    
    # 验证数据库配置
    if not config.database.host:
        errors.append("数据库主机地址不能为空")
    
    if not config.database.user:
        errors.append("数据库用户名不能为空")
    
    if not config.database.database:
        errors.append("数据库名称不能为空")
    
    # 验证模型配置
    if config.model_type == 'cloud' and not config.qwen_api_key:
        errors.append("使用 cloud 模式时必须提供 QWEN_API_KEY")
    
    if not config.qwen_model_name:
        errors.append("Qwen 模型名称不能为空")
    
    is_valid = len(errors) == 0
    
    if is_valid:
        logger.info("配置验证通过")
    else:
        logger.error(f"配置验证失败: {', '.join(errors)}")
    
    return is_valid, errors


def get_config_summary(config: AppConfig) -> dict:
    """
    获取配置摘要（隐藏敏感信息）
    
    Args:
        config: 应用配置对象
        
    Returns:
        dict: 配置摘要字典
    """
    return {
        'database': {
            'host': config.database.host,
            'port': config.database.port,
            'user': config.database.user,
            'database': config.database.database,
            'pool_size': config.database.pool_size,
            'password': '***' if config.database.password else '(empty)'
        },
        'redis': {
            'host': config.redis.host,
            'port': config.redis.port,
            'db': config.redis.db,
            'cache_enabled': config.redis.cache_enabled,
            'cache_ttl': config.redis.cache_ttl,
            'password': '***' if config.redis.password else '(empty)'
        },
        'model_type': config.model_type,
        'qwen_model_name': config.qwen_model_name,
        'qwen_api_key': '***' if config.qwen_api_key else '(not set)',
        'log_level': config.log_level,
        'debug': config.debug,
        'enable_streaming': config.enable_streaming,
        'streaming_timeout': config.streaming_timeout,
        'retrieval_limits': {
            'normal': {
                'max_terms': config.retrieval_normal_max_terms,
                'max_logics': config.retrieval_normal_max_logics,
                'max_events': config.retrieval_normal_max_events,
                'table_keep': config.retrieval_normal_table_keep,
                'global_keep': config.retrieval_normal_global_keep,
                'dictionary_keep': config.retrieval_normal_dictionary_keep,
            },
            'expanded': {
                'max_terms': config.retrieval_expanded_max_terms,
                'max_logics': config.retrieval_expanded_max_logics,
                'max_events': config.retrieval_expanded_max_events,
                'table_keep': config.retrieval_expanded_table_keep,
                'global_keep': config.retrieval_expanded_global_keep,
                'dictionary_keep': config.retrieval_expanded_dictionary_keep,
            }
        }
    }


# 全局配置实例（延迟加载）
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    获取全局配置实例（单例模式）
    
    Returns:
        AppConfig: 应用配置对象
    """
    global _config
    if _config is None:
        _config = load_config()
        # 验证配置
        is_valid, errors = validate_config(_config)
        if not is_valid:
            logger.error(f"配置验证失败: {', '.join(errors)}")
            raise ValueError(f"配置验证失败: {', '.join(errors)}")
    return _config


def reload_config() -> AppConfig:
    """
    重新加载配置
    
    Returns:
        AppConfig: 新的应用配置对象
    """
    global _config
    load_dotenv(override=True)  # 重新加载 .env 文件
    _config = load_config()
    return _config


# 导出配置访问函数
__all__ = [
    'DatabaseConfig',
    'AppConfig',
    'load_config',
    'validate_config',
    'get_config',
    'reload_config',
    'get_config_summary'
]
