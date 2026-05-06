import logging
from typing import Dict, Any
import re
from datetime import datetime, timedelta

# 创建日志记录器
logger = logging.getLogger(__name__)

class NLUService:
    def __init__(self):
        # 预定义的指标和维度关键词
        self.metric_keywords = [
            '销售额', '销售', '收入', '营收', '利润', '成本', '数量', '订单数', '用户数', '访问量',
            'amount', 'sales', 'revenue', 'profit', 'cost', 'quantity', 'orders', 'users', 'visits'
        ]
        
        self.dimension_keywords = [
            '产品', '地区', '城市', '区域', '月份', '季度', '年份', '客户', '渠道', '部门',
            'product', 'region', 'city', 'area', 'month', 'quarter', 'year', 'customer', 'channel', 'department'
        ]
        
        logger.info(f"NLUParser initialized with {len(self.metric_keywords)} metric keywords and {len(self.dimension_keywords)} dimension keywords")

    def parse_time_range(self, text: str) -> Dict[str, Any]:
        """
        解析自然语言中的时间范围
        """
        logger.debug(f"Parsing time range from text: {text}")
        text = text.lower()
        today = datetime.now()
        current_year = today.year
        current_month = today.month  # 1-12
        
        # 识别“上月”、“上个季度”、“上一年"
        if any(kw in text for kw in ['上月', '上个月', 'last month']):
            last_month = 12 if current_month == 1 else current_month - 1
            last_year = current_year - 1 if current_month == 1 else current_year
            
            start_date = datetime(last_year, last_month, 1)
            end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            logger.info(f"Detected 'last month' in query, time range: {start_date.date()} to {end_date.date()}")
            return {
                'start': start_date,
                'end': end_date,
                'type': 'month'
            }
        
        if any(kw in text for kw in ['上季度', '上个季度', 'last quarter']):
            quarter = (current_month - 1) // 3
            if quarter == 0:
                start_quarter = 3
                start_year = current_year - 1
            else:
                start_quarter = quarter - 1
                start_year = current_year
            
            start_month = start_quarter * 3 + 1
            end_month = start_month + 2
            end_day = (datetime(start_year, end_month + 1, 1) - timedelta(days=1)).day
            
            start_date = datetime(start_year, start_month, 1)
            end_date = datetime(start_year, end_month, end_day)
            
            logger.info(f"Detected 'last quarter' in query, time range: {start_date.date()} to {end_date.date()}")
            return {
                'start': start_date,
                'end': end_date,
                'type': 'quarter'
            }
        
        if any(kw in text for kw in ['上一年', '去年', 'last year']):
            logger.info(f"Detected 'last year' in query, time range: {current_year - 1}-01-01 to {current_year - 1}-12-31")
            return {
                'start': datetime(current_year - 1, 1, 1),
                'end': datetime(current_year - 1, 12, 31),
                'type': 'year'
            }
        
        # 识别“最近7天”、“最近30天"
        recent_days_match = re.search(r'最近(\d+)天|recently\s+(\d+)\s+days?', text)
        if recent_days_match:
            days = int(recent_days_match.group(1) or recent_days_match.group(2))
            start_date = today - timedelta(days=days)
            logger.info(f"Detected 'last {days} days' in query, time range: {start_date.date()} to {today.date()}")
            return {
                'start': start_date,
                'end': today,
                'type': 'days'
            }
        
        # 识别“本月”、“本季度”、“本年"
        if any(kw in text for kw in ['本月', '这个月', 'this month']):
            start_date = datetime(current_year, current_month, 1)
            end_date = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            logger.info(f"Detected 'this month' in query, time range: {start_date.date()} to {end_date.date()}")
            return {
                'start': start_date,
                'end': end_date,
                'type': 'month'
            }
        
        if any(kw in text for kw in ['本季度', '这个季度', 'this quarter']):
            quarter = (current_month - 1) // 3
            start_month = quarter * 3 + 1
            end_month = start_month + 2
            end_day = (datetime(current_year, end_month + 1, 1) - timedelta(days=1)).day
            
            start_date = datetime(current_year, start_month, 1)
            end_date = datetime(current_year, end_month, end_day)
            
            logger.info(f"Detected 'this quarter' in query, time range: {start_date.date()} to {end_date.date()}")
            return {
                'start': start_date,
                'end': end_date,
                'type': 'quarter'
            }
        
        if any(kw in text for kw in ['今年', '本年', 'this year']):
            logger.info(f"Detected 'this year' in query, time range: {current_year}-01-01 to {current_year}-12-31")
            return {
                'start': datetime(current_year, 1, 1),
                'end': datetime(current_year, 12, 31),
                'type': 'year'
            }
        
        # 默认：无时间范围
        logger.info("No time range detected in query, using 'all' time range")
        return {
            'start': None,
            'end': None,
            'type': 'all'
        }

    async def process_natural_language_query(self, text: str) -> Dict[str, Any]:
        """
        处理自然语言查询，返回解析结果
        """
        logger.info(f"Processing natural language query: {text}")
        clean_text = text.strip().lower()
        
        # 提取时间范围
        time_range = self.parse_time_range(clean_text)
        
        # 提取指标（数值型字段）
        metric = None
        for kw in self.metric_keywords:
            if kw in clean_text:
                metric = kw
                logger.info(f"Detected metric: {metric}")
                break
        
        # 如果没有找到明确指标，使用默认
        if not metric:
            metric = '销售额'
            logger.info("No specific metric detected, using default: 销售额")
        
        # 提取维度（分类字段）
        dimension = None
        for kw in self.dimension_keywords:
            if kw in clean_text:
                dimension = kw
                logger.info(f"Detected dimension: {dimension}")
                break
        
        # 如果没有找到明确维度，使用默认
        if not dimension:
            dimension = '产品'
            logger.info("No specific dimension detected, using default: 产品")
        
        # 提取实体
        entities = {
            'metric': metric,
            'dimension': dimension
        }
        
        result = {
            'text': text,
            'entities': entities,
            'time_range': time_range
        }
        
        logger.info(f"NLU parsing completed successfully: metric='{metric}', dimension='{dimension}', time_range='{time_range['type']}'")
        return result


# 为了兼容性，创建 NLUParser 别名
NLUParser = NLUService