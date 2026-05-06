import logging
from typing import Dict, Any
import pandas as pd
import mysql.connector
from src.sql_generator import SQLGenerator
from src.sql_generator_qwen import SQLGeneratorQwen
from src.cache_service import CacheService
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 创建日志记录器
logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self):
        self.active_data_source = None
        self.rule_based_generator = SQLGenerator()
        self.qwen_generator = SQLGeneratorQwen()
        self.cache_service = CacheService(max_size=1000, default_ttl=300)  # 1000个缓存项，5分钟过期
        
        # 获取模型类型配置
        self.model_type = os.getenv('MODEL_TYPE', 'local').lower()
        
        # 验证模型类型
        if self.model_type not in ['local', 'cloud']:
            logger.warning(f"Invalid MODEL_TYPE '{self.model_type}', defaulting to 'local'")
            self.model_type = 'local'
        
        logger.info(f"QueryService initialized with model_type='{self.model_type}', cache size: 1000, TTL: 300 seconds")
        
    def set_active_data_source(self, data_source: Dict[str, Any]):
        """
        设置当前激活的数据源
        """
        self.active_data_source = data_source
        logger.info(f"Active data source set: {data_source['name']} (ID: {data_source['id']}, Type: {data_source['type']})")

    def execute_query(self, nlu_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行查询并返回结果
        使用智能路由选择最佳SQL生成器
        支持缓存机制以提高性能
        """
        logger.info(f"Starting query execution for: {nlu_result['original_text'][:100]}...")
        
        if not self.active_data_source:
            error_msg = "No active data source available"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        metric = nlu_result['entities']['metric']
        dimension = nlu_result['entities']['dimension']
        time_range = nlu_result['time_range']
        data_source_id = self.active_data_source['id']
        
        # 尝试从缓存获取结果
        cached_result = self.cache_service.get(
            query=nlu_result['original_text'],
            data_source_id=data_source_id,
            time_range=time_range
        )
        
        if cached_result:
            logger.info(f"Cache hit for query: {nlu_result['original_text'][:50]}...")
            return cached_result
        
        # 智能路由决策
        generator = self._select_sql_generator(nlu_result)
        logger.info(f"Selected SQL generator: {'Qwen' if generator == self.qwen_generator else 'Rule-based'} for query")
        
        if self.active_data_source['type'] == 'excel':
            logger.info(f"Executing Excel query: metric='{metric}', dimension='{dimension}', time_range='{time_range}'")
            result = self._execute_excel_query(metric, dimension, time_range, generator)
        elif self.active_data_source['type'] == 'mysql':
            logger.info(f"Executing MySQL query: metric='{metric}', dimension='{dimension}', time_range='{time_range}'")
            result = self._execute_mysql_query(metric, dimension, time_range, generator)
        else:
            error_msg = f"Unsupported data source type: {self.active_data_source['type']}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 将结果存入缓存
        self.cache_service.set(
            query=nlu_result['original_text'],
            data_source_id=data_source_id,
            time_range=time_range,
            result=result
        )
        logger.info(f"Query result cached for: {nlu_result['original_text'][:50]}...")
        
        logger.info(f"Query execution completed successfully for: {nlu_result['original_text'][:100]}...")
        return result

    def _select_sql_generator(self, nlu_result: Dict[str, Any]) -> any:
        """
        智能选择SQL生成器
        
        决策逻辑：
        1. 如果查询包含复杂模式（趋势、对比、多条件），使用大模型
        2. 否则使用规则引擎（更稳定、更快）
        """
        text = nlu_result['original_text']
        entities = nlu_result['entities']
        
        # 复杂查询模式检测
        complex_patterns = [
            '和', '与', '相比', '对比',  # 比较
            '趋势', '变化', '增长', '下降',  # 趋势
            '平均', '均值',  # 统计
            '前', '最高', '最低',  # 排序
            '哪些', '什么',  # 开放式问题
            '为什么', '如何'  # 解释性问题
        ]
        
        # 检查是否包含复杂模式
        has_complex_pattern = any(pattern in text for pattern in complex_patterns)
        
        # 检查是否有多个指标或维度
        has_multiple_entities = len([k for k, v in entities.items() if v]) > 2
        
        # 如果是复杂查询，使用大模型；否则使用规则引擎
        if has_complex_pattern or has_multiple_entities:
            logger.debug(f"Complex pattern detected in query: {text}")
            logger.info("Selecting Qwen SQL generator for complex query")
            return self.qwen_generator
        else:
            logger.debug(f"Simple pattern detected in query: {text}")
            logger.info("Selecting rule-based SQL generator for simple query")
            return self.rule_based_generator
    
    def _execute_excel_query(self, metric: str, dimension: str, time_range: Dict[str, Any], generator: any) -> Dict[str, Any]:
        """
        执行Excel查询
        """
        logger.info(f"Starting Excel query execution: metric='{metric}', dimension='{dimension}'")
        
        # 读取Excel文件
        file_path = self.active_data_source['file_path']
        logger.info(f"Reading Excel file: {file_path}")
        df = pd.read_excel(file_path)
        
        # 根据时间范围过滤
        if time_range['start'] and time_range['end']:
            # 假设有一个日期列
            logger.info(f"Applying time range filter: {time_range['start']} to {time_range['end']}")
            df['date'] = pd.to_datetime(df.get('date', 'created_at'))
            start = pd.to_datetime(time_range['start'])
            end = pd.to_datetime(time_range['end'])
            df = df[(df['date'] >= start) & (df['date'] <= end)]
            logger.info(f"Filtered {len(df)} rows after time range filtering")
        
        # 按维度分组，计算指标总和
        grouped = df.groupby(dimension)[metric].sum().reset_index()
        sorted_data = grouped.sort_values(by=metric, ascending=False)
        
        # 转换为图表所需格式
        chart_data = []
        for _, row in sorted_data.iterrows():
            chart_data.append({
                'label': row[dimension],
                'value': float(row[metric])
            })
        
        max_value = max(item['value'] for item in chart_data) if chart_data else 100
        
        # 生成SQL语句
        sql = generator.generate_sql(nlu_result={
            'entities': {'metric': metric, 'dimension': dimension},
            'time_range': time_range,
            'original_text': ""
        }, table_name="excel_data")
        logger.info(f"Generated SQL for Excel query: {sql[:100]}...")
        
        logger.info(f"Excel query completed successfully, returning {len(chart_data)} rows")
        return {
            'chartType': 'bar',
            'data': chart_data[:10],
            'headers': [dimension, metric],
            'rows': [[item['label'], item['value']] for item in chart_data[:10]],
            'maxValue': max_value,
            'sql': sql,
            'raw': df.to_dict('records')
        }

    def _execute_mysql_query(self, metric: str, dimension: str, time_range: Dict[str, Any], generator: any) -> Dict[str, Any]:
        """
        执行MySQL查询
        """
        logger.info(f"Starting MySQL query execution: metric='{metric}', dimension='{dimension}'")
        
        try:
            # 连接数据库
            conn_str = self.active_data_source['connection_string']
            logger.info(f"Connecting to MySQL database using connection string: {conn_str[:50]}...")
            db_config = self._parse_connection_string(conn_str)
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)
            
            # 使用选定的生成器生成SQL
            sql = generator.generate_sql(nlu_result={
                'entities': {'metric': metric, 'dimension': dimension},
                'time_range': time_range,
                'original_text': ""
            }, table_name="sales")
            logger.info(f"Generated SQL for MySQL query: {sql}")
            
            # 执行查询
            logger.info("Executing MySQL query")
            cursor.execute(sql)
            results = cursor.fetchall()
            logger.info(f"MySQL query returned {len(results)} rows")
            
            # 转换为图表格式
            chart_data = [{
                'label': row[dimension],
                'value': float(row['total'])
            } for row in results]
            
            max_value = max(item['value'] for item in chart_data) if chart_data else 100
            
            logger.info(f"MySQL query completed successfully, returning {len(chart_data)} rows")
            return {
                'chartType': 'bar',
                'data': chart_data,
                'headers': [dimension, metric],
                'rows': [[item['label'], item['value']] for item in chart_data],
                'maxValue': max_value,
                'sql': sql,
                'raw': results
            }
        except mysql.connector.Error as e:
            error_msg = f"MySQL database error: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to execute MySQL query: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            if 'connection' in locals():
                connection.close()
                logger.info("MySQL connection closed")

    def infer_chart_type(self, result: dict) -> str:
        """
        根据查询结果推断合适的图表类型
        
        逻辑：
        * 如果只有1列数据 -> 'table'
        * 如果有2列且第一列是时间类型 -> 'line'
        * 如果有2列且第一列是类别 -> 'bar'
        * 如果有2列且数据适合占比分析 -> 'pie'
        * 默认 -> 'table'
        
        Args:
            result: 查询结果字典，包含'headers'和'rows'字段
            
        Returns:
            str: 'bar', 'line', 'pie', 或 'table'
        """
        if not result or 'headers' not in result:
            return 'table'
        
        headers = result['headers']
        
        # 如果只有1列数据，返回table
        if len(headers) <= 1:
            return 'table'
        
        # 如果有2列数据，判断图表类型
        if len(headers) == 2:
            first_column = headers[0].lower()
            
            # 检查第一列是否为时间类型（包含时间相关关键词）
            time_keywords = ['date', 'time', '年', '月', '日', '周', '季度']
            is_time_column = any(keyword in first_column for keyword in time_keywords)
            
            if is_time_column:
                return 'line'
            
            # 检查是否适合占比分析（数值型指标，且数值分布适合pie图）
            # 简单判断：如果数据行数较少（<=5）且值相对集中，适合pie图
            if 'rows' in result and len(result['rows']) <= 5:
                values = [row[1] for row in result['rows'] if len(row) > 1]
                if all(isinstance(v, (int, float)) for v in values) and sum(values) > 0:
                    # 计算占比分布，如果存在一个主导项，适合pie图
                    total = sum(values)
                    if total > 0:
                        proportions = [v / total for v in values]
                        max_proportion = max(proportions)
                        # 如果最大占比超过50%，适合pie图
                        if max_proportion > 0.5:
                            return 'pie'
            
            # 默认为bar图
            return 'bar'
        
        # 默认为table
        return 'table'
    
    def save_to_session_history(self, session_id: str, query_text: str, result: dict, chart_type: str) -> bool:
        """
        将查询保存到 query_history 表
        关联到指定的 session_id
        保存：query_text, result (JSON), chart_type, created_at
        调用 session_service.add_message_to_session() 更新会话历史
        
        Args:
            session_id: 会话ID
            query_text: 原始查询文本
            result: 查询结果字典
            chart_type: 推断的图表类型
            
        Returns:
            bool: 是否成功保存
        """
        try:
            # 导入必要的模块
            from src.session_service import SessionService
            from src.models.session_model import QueryHistory
            from src.database_service import DatabaseService
            
            # 创建数据库服务实例
            db_service = DatabaseService()
            
            # 将结果转换为JSON字符串
            result_json = str(result)  # 简单转换，实际项目中可能需要更复杂的序列化
            
            # 创建查询历史记录
            query_history = QueryHistory(
                session_id=session_id,
                query_text=query_text,
                result_data=result_json,
                chart_type=chart_type
            )
            
            # 保存到数据库
            db_service.add_query_history(query_history)
            
            # 更新会话历史
            session_service = SessionService()
            session_service.add_message_to_session(session_id, "user", query_text)
            session_service.add_message_to_session(session_id, "assistant", f"已为您分析：{query_text}")
            
            logger.info(f"Saved query to session history: session_id={session_id}, query='{query_text[:50]}...'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save query to session history: {str(e)}")
            return False
    
    def parse_time_expressions(self, text: str) -> str:
        """
        解析时间表达式如"上月"、"本周"、"最近7天"
        转换为具体的日期范围
        
        Args:
            text: 包含时间表达式的原始文本
            
        Returns:
            str: 处理后的文本，时间表达式已替换为具体日期范围
        """
        import re
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        # 当前日期
        today = datetime.now().date()
        
        # 定义时间表达式映射
        time_patterns = [
            # 上月
            (r'上月', lambda: f"{((today.replace(day=1) - relativedelta(months=1)).strftime('%Y-%m-01'))} 到 {((today.replace(day=1) - relativedelta(days=1)).strftime('%Y-%m-%d'))}"),
            # 本月
            (r'本月', lambda: f"{today.replace(day=1).strftime('%Y-%m-01')} 到 {today.strftime('%Y-%m-%d')}"),
            # 上周
            (r'上周', lambda: f"{(today - timedelta(days=today.weekday()+7)).strftime('%Y-%m-%d')} 到 {(today - timedelta(days=today.weekday()+1)).strftime('%Y-%m-%d')}"),
            # 本周
            (r'本周', lambda: f"{(today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')} 到 {today.strftime('%Y-%m-%d')}"),
            # 最近7天
            (r'最近7天', lambda: f"{(today - timedelta(days=6)).strftime('%Y-%m-%d')} 到 {today.strftime('%Y-%m-%d')}"),
            # 最近30天
            (r'最近30天', lambda: f"{(today - timedelta(days=29)).strftime('%Y-%m-%d')} 到 {today.strftime('%Y-%m-%d')}"),
            # 去年
            (r'去年', lambda: f"{today.year-1}-01-01 到 {today.year-1}-12-31"),
            # 今年
            (r'今年', lambda: f"{today.year}-01-01 到 {today.strftime('%Y-%m-%d')}"),
        ]
        
        # 逐个替换时间表达式
        result_text = text
        for pattern, replacement_func in time_patterns:
            if re.search(pattern, result_text):
                try:
                    # 获取替换后的日期范围
                    date_range = replacement_func()
                    result_text = re.sub(pattern, date_range, result_text)
                    logger.debug(f"Replaced '{pattern}' with date range: {date_range}")
                except Exception as e:
                    logger.warning(f"Failed to parse time expression '{pattern}': {str(e)}")
                    continue
        
        return result_text
    
    def _parse_connection_string(self, conn_str: str) -> Dict[str, Any]:
        """
        解析数据库连接字符串
        格式：mysql://user:password@host:port/database
        """
        from urllib.parse import urlparse
        logger.debug(f"Parsing connection string: {conn_str}")
        parsed = urlparse(conn_str)
        
        return {
            'host': parsed.hostname,
            'port': parsed.port or 3306,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/')
        }