"""
日志配置模块

配置和初始化应用日志系统。
"""

import logging
import os
from datetime import datetime

# 创建日志目录
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(log_dir, exist_ok=True)

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 创建文件处理器
log_file = os.path.join(log_dir, f"backend_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(formatter)

# 🆕 配置根日志记录器（捕获所有模块的日志）
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

# 配置 ChatBI 专用日志记录器
logger = logging.getLogger("ChatBI")
logger.setLevel(logging.INFO)
# ChatBI logger 不需要单独的 handler，会继承 root logger 的 handler

# 为常用模块创建别名
# 这样可以在其他模块中直接从src.utils导入logger
__all__ = ["logger"]