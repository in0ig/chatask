import sys
from unittest.mock import MagicMock

# 创建模拟的mysql包
mock_mysql = MagicMock()
mock_mysql.connector = MagicMock()
mock_mysql.connector.connect = MagicMock()
mock_mysql.connector.Error = type('Error', (Exception,), {})

# 将模拟的包添加到sys.modules中
sys.modules['mysql'] = mock_mysql
sys.modules['mysql.connector'] = mock_mysql.connector