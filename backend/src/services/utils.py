from typing import Dict, Any
import hashlib

def generate_query_hash(text: str) -> str:
    """
    生成查询的哈希值，用于缓存键
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def format_currency(value: float) -> str:
    """
    格式化货币显示
    """
    if not isinstance(value, (int, float)):
        return str(value)
    return f'¥{value:,.0f}'

def format_number(value: float) -> str:
    """
    格式化数字（千分位）
    """
    if not isinstance(value, (int, float)):
        return str(value)
    return f'{value:,}'