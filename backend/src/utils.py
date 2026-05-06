import logging
import os
from datetime import datetime
from dotenv import load_dotenv


def setup_logging():
    """
    设置统一的日志系统
    配置日志输出到backend/backend.log文件
    日志格式：[时间] [级别] [模块] - 消息
    """
    
    # 加载 .env 文件中的环境变量
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        print(f"已成功加载环境变量文件: {env_path}")
    else:
        print(f".env 文件不存在: {env_path}，将使用系统环境变量")
    
    # 创建logs目录（如果不存在）
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend')
    try:
        os.makedirs(log_dir, exist_ok=True)
        print(f"日志目录已准备就绪: {log_dir}")
    except Exception as e:
        print(f"创建日志目录失败: {log_dir}, 错误: {str(e)}")
        raise
    
    # 创建或清空日志文件
    log_file = os.path.join(log_dir, 'backend.log')
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== 日志系统启动于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        print(f"日志文件已初始化: {log_file}")
    except Exception as e:
        print(f"初始化日志文件失败: {log_file}, 错误: {str(e)}")
        raise
    
    # 配置日志格式 - 普通级别使用简洁格式，错误级别使用详细格式
    simple_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] [%(name)-15s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] [%(name)-15s] [%(filename)s:%(lineno)d %(funcName)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 为不同日志级别设置不同的格式器
    class LevelFormatter(logging.Formatter):
        def format(self, record):
            if record.levelno >= logging.ERROR:
                return detailed_formatter.format(record)
            else:
                return simple_formatter.format(record)
    
    # 创建文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(LevelFormatter())
    print(f"已创建文件处理器，日志输出到: {log_file}")
    
    # 创建控制台处理器（可选，用于开发调试）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LevelFormatter())
    print("已创建控制台处理器")
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 添加处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 为特定模块设置日志级别
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.INFO)
    print("已为 uvicorn 模块设置日志级别为 INFO")
    
    print("日志系统配置完成")
    return logging.getLogger('main')

# 创建全局日志记录器
logger = setup_logging()


# 移除get_db_session函数，因为数据库连接现在由src/database.py处理
# 测试模式下，src/database.py会使用SQLite内存数据库
# 生产模式下，src/database.py会使用MySQL数据库

# 保留MockSession和MockQuery类，但不再作为get_db_session的实现
# 这些类现在仅用于测试框架的其他部分

class MockSession:
    """用于测试的模拟数据库会话"""
    
    def __init__(self):
        self.added_objects = []
        self.committed = False
        self.refreshed = False
        self.rollbacked = False
        
    def add(self, obj):
        self.added_objects.append(obj)
        
    def commit(self):
        self.committed = True
        
    def refresh(self, obj):
        self.refreshed = True
        
    def rollback(self):
        self.rollbacked = True
        
    def query(self, model):
        return MockQuery(model)
        

class MockQuery:
    """用于测试的模拟查询"""
    
    def __init__(self, model):
        self.model = model
        self.filter_conditions = []
        self.order_by_conditions = []
        
    def filter(self, *conditions):
        self.filter_conditions.extend(conditions)
        return self
        
    def order_by(self, *conditions):
        self.order_by_conditions.extend(conditions)
        return self
        
    def first(self):
        # 返回一个空的模拟对象
        return None
        
    def all(self):
        # 返回一个空列表
        return []
        
# 为测试提供一个简单的get_db_session实现
def get_db_session_for_test():
    """为测试提供一个简单的数据库会话"""
    return MockSession()