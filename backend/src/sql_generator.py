from typing import Dict, List, Any, Optional
import re

class SQLGenerator:
    def __init__(self):
        # 定义常见的指标和维度关键词映射
        self.metric_keywords = {
            '销售额': ['sales', 'revenue', 'amount', 'total'],
            '利润': ['profit', 'earnings', 'net_income'],
            '数量': ['quantity', 'count', 'number', 'units'],
            '成本': ['cost', 'expense'],
            '订单数': ['orders', 'transactions'],
            '客户数': ['customers', 'users', 'clients'],
            '转化率': ['conversion', 'rate'],
            '增长率': ['growth', 'increase'],
            '平均值': ['average', 'avg', 'mean'],
            '总和': ['sum', 'total'],
            '最大值': ['max', 'highest'],
            '最小值': ['min', 'lowest']
        }
        
        self.dimension_keywords = {
            '产品': ['product', 'item', 'goods', 'category'],
            '地区': ['region', 'area', 'location', 'city', 'province', 'country'],
            '时间': ['time', 'date', 'year', 'month', 'quarter', 'week', 'day'],
            '客户': ['customer', 'user', 'client'],
            '渠道': ['channel', 'source', 'medium'],
            '部门': ['department', 'team', 'division'],
            '员工': ['employee', 'staff']
        }
        
        # 时间表达式映射
        self.time_patterns = {
            '今天': r'今天|今日|this\s*day',
            '昨天': r'昨天|yesterday',
            '前天': r'前天|the\s*day\s*before\s* yesterday',
            '本周': r'本周|this\s*week',
            '上周': r'上周|last\s*week',
            '本月': r'本月|this\s*month',
            '上月': r'上月|last\s*month',
            '本季度': r'本季度|this\s*quarter',
            '上季度': r'上季度|last\s*quarter',
            '本年': r'本年|this\s*year',
            '去年': r'去年|last\s*year'
        }
        
        # SQL 模板
        self.sql_templates = {
            'aggregate': "SELECT {aggregation}({metric}) as {metric}, {dimension} FROM {table} WHERE {time_condition} GROUP BY {dimension} ORDER BY {aggregation}({metric}) {order} LIMIT {limit}",
            'simple': "SELECT {metric}, {dimension} FROM {table} WHERE {time_condition} ORDER BY {metric} {order} LIMIT {limit}",
            'count': "SELECT COUNT(*) as count, {dimension} FROM {table} WHERE {time_condition} GROUP BY {dimension} ORDER BY count {order} LIMIT {limit}",
            'trend': "SELECT {aggregation}({metric}) as {metric}, {time_dimension} FROM {table} WHERE {time_condition} GROUP BY {time_dimension} ORDER BY {time_dimension} ASC"
        }
    
    def generate_sql(self, nlu_result: Dict[str, Any], table_name: str = "sales_data") -> str:
        """
        根据NLU解析结果生成SQL查询语句
        
        Args:
            nlu_result: NLU解析结果，包含time_range和entities
            table_name: 数据表名，默认为sales_data
            
        Returns:
            生成的SQL查询语句
        """
        
        # 提取NLU结果中的关键信息
        entities = nlu_result.get('entities', {})
        time_range = nlu_result.get('time_range', {})
        
        # 提取指标和维度
        metric = self._extract_metric(entities)
        dimension = self._extract_dimension(entities)
        time_dimension = self._extract_time_dimension(time_range)
        
        # 确定聚合函数
        aggregation = self._determine_aggregation(metric)
        
        # 确定排序方式
        order = self._determine_order(metric)
        
        # 生成时间条件
        time_condition = self._generate_time_condition(time_range, time_dimension)
        
        # 根据查询类型选择SQL模板
        sql_template = self._select_sql_template(metric, dimension, time_range)
        
        # 填充模板
        sql = sql_template.format(
            aggregation=aggregation,
            metric=metric,
            dimension=dimension,
            time_dimension=time_dimension,
            table=table_name,
            time_condition=time_condition,
            order=order,
            limit=10
        )
        
        return sql.strip()
    
    def _extract_metric(self, entities: Dict[str, Any]) -> str:
        """
        从实体中提取指标
        """
        # 优先使用明确的指标
        if 'metric' in entities:
            return entities['metric']
        
        # 如果没有明确指标，尝试从查询中推断
        # 这里可以扩展为更复杂的逻辑
        return '销售额'  # 默认指标
    
    def _extract_dimension(self, entities: Dict[str, Any]) -> str:
        """
        从实体中提取维度
        """
        # 优先使用明确的维度
        if 'dimension' in entities:
            return entities['dimension']
        
        # 如果没有明确维度，尝试从查询中推断
        # 这里可以扩展为更复杂的逻辑
        return '产品'  # 默认维度
    
    def _extract_time_dimension(self, time_range: Dict[str, Any]) -> str:
        """
        从时间范围中提取时间维度
        """
        # 如果有明确的时间维度，使用它
        if 'time_dimension' in time_range:
            return time_range['time_dimension']
        
        # 否则根据时间范围类型推断
        time_type = time_range.get('type', 'month')
        
        time_mapping = {
            'day': '日期',
            'week': '周',
            'month': '月份',
            'quarter': '季度',
            'year': '年'
        }
        
        return time_mapping.get(time_type, '月份')
    
    def _determine_aggregation(self, metric: str) -> str:
        """
        根据指标确定聚合函数
        """
        # 常见的聚合函数映射
        aggregation_map = {
            '平均值': 'AVG',
            '总和': 'SUM',
            '最大值': 'MAX',
            '最小值': 'MIN',
            '数量': 'COUNT',
            '增长率': 'AVG'
        }
        
        # 检查指标是否包含特定关键词
        for keyword, agg in aggregation_map.items():
            if keyword in metric:
                return agg
        
        # 默认使用SUM
        return 'SUM'
    
    def _determine_order(self, metric: str) -> str:
        """
        根据指标确定排序方式
        """
        # 如果指标包含"最高"、"最大"、"增长"等词，按降序排列
        if any(word in metric for word in ['最高', '最大', '增长', '最多', 'top', 'highest', 'max']):
            return 'DESC'
        
        # 如果指标包含"最低"、"最小"、"减少"等词，按升序排列
        if any(word in metric for word in ['最低', '最小', '减少', '最少', 'lowest', 'min']):
            return 'ASC'
        
        # 默认降序
        return 'DESC'
    
    def _generate_time_condition(self, time_range: Dict[str, Any], time_dimension: str) -> str:
        """
        生成时间条件
        """
        if not time_range:
            return "1=1"  # 无时间限制
        
        start_time = time_range.get('start')
        end_time = time_range.get('end')
        time_type = time_range.get('type')
        
        if start_time and end_time:
            # 有明确的时间范围
            return f"{time_dimension} BETWEEN '{start_time}' AND '{end_time}'"
        elif start_time:
            # 只有开始时间
            return f"{time_dimension} >= '{start_time}'"
        elif end_time:
            # 只有结束时间
            return f"{time_dimension} <= '{end_time}'"
        elif time_type:
            # 根据时间类型生成条件
            return self._generate_time_condition_by_type(time_type, time_dimension)
        
        return "1=1"
    
    def _generate_time_condition_by_type(self, time_type: str, time_dimension: str) -> str:
        """
        根据时间类型生成条件
        """
        # 这里可以扩展为更复杂的逻辑，使用数据库函数
        # 简化版本：使用相对时间
        
        # 由于我们不知道具体的数据库结构，使用简单的日期比较
        # 在实际应用中，应该使用数据库的日期函数
        
        # 为简化，返回一个通用条件
        return f"{time_dimension} IS NOT NULL"
    
    def _select_sql_template(self, metric: str, dimension: str, time_range: Dict[str, Any]) -> str:
        """
        根据查询特征选择SQL模板
        """
        # 如果有明确的时间维度和指标，使用趋势模板
        if time_range.get('type') in ['day', 'week', 'month', 'quarter', 'year'] and dimension != '时间':
            return self.sql_templates['trend']
        
        # 如果查询的是数量，使用计数模板
        if any(word in metric for word in ['数量', 'count', 'number', '次数']):
            return self.sql_templates['count']
        
        # 如果有维度和指标，使用聚合模板
        if dimension and metric:
            return self.sql_templates['aggregate']
        
        # 如果只有指标，使用简单模板
        if metric:
            return self.sql_templates['simple']
        
        # 默认聚合模板
        return self.sql_templates['aggregate']