"""
SQL执行和结果处理服务

任务 5.4.4 的核心实现
实现SQL查询的安全执行和资源控制，添加查询超时、内存限制和并发控制，
创建结果集的格式化、优化和流式返回，支持大结果集的分页处理和性能优化
"""

import asyncio
import logging
import re
import time

from src.utils.mysql_datasource_docker_remap import remap_mysql_datasource_host
from typing import Dict, Any, Optional, List, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# 可选的数据库驱动
try:
    import pymysql
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False
    logger.warning("pymysql not installed, MySQL support disabled")

try:
    import pymssql
    PYMSSQL_AVAILABLE = True
except ImportError:
    PYMSSQL_AVAILABLE = False
    logger.warning("pymssql not installed, SQL Server support disabled")

try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


class DatabaseType(Enum):
    """数据库类型"""
    MYSQL = "mysql"
    SQLSERVER = "sqlserver"
    POSTGRESQL = "postgresql"


@dataclass
class ExecutionConfig:
    """执行配置"""
    timeout_seconds: int = 30
    max_rows: int = 10000
    max_memory_mb: int = 100
    enable_streaming: bool = True
    page_size: int = 1000
    max_concurrent_queries: int = 10


@dataclass
class QueryResult:
    """查询结果"""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    execution_time: float
    is_truncated: bool = False
    has_more: bool = False
    page_info: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ExecutionStatistics:
    """执行统计"""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    timeout_queries: int = 0
    average_execution_time: float = 0.0
    total_rows_returned: int = 0
    cache_hits: int = 0


class SQLExecutionError(Exception):
    """SQL执行异常"""
    def __init__(self, message: str, error_code: str = None, original_error: Exception = None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error


class SQLExecutorService:
    """SQL执行服务"""
    
    def __init__(self, config: ExecutionConfig = None):
        """初始化SQL执行服务"""
        self.config = config or ExecutionConfig()
        
        # 并发控制
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_queries)
        self._active_queries = 0
        
        # 统计信息
        self.stats = ExecutionStatistics()
        
        # 结果缓存（简单的内存缓存）
        self._result_cache: Dict[str, QueryResult] = {}
        self._cache_ttl = 300  # 5分钟缓存
        self._cache_timestamps: Dict[str, float] = {}
        
        logger.info(f"SQL执行服务初始化完成，配置: {self.config}")
    
    def _fix_union_syntax(self, sql: str) -> str:
        """
        修复 AI 生成的 UNION/UNION ALL 语法问题。
        MySQL 中 UNION 子查询若含 ORDER BY 或 LIMIT，必须用括号包裹，
        否则报 1064 语法错误。此方法自动为每个子查询加括号。
        """
        import re
        if not re.search(r'\bUNION\b', sql, re.IGNORECASE):
            return sql

        # 按 UNION ALL 或 UNION 分割（保留分隔符）
        pattern = r'(\bUNION\s+ALL\b|\bUNION\b)'
        parts = re.split(pattern, sql, flags=re.IGNORECASE)

        fixed_parts = []
        for part in parts:
            stripped = part.strip()
            if re.match(r'^UNION(\s+ALL)?$', stripped, re.IGNORECASE):
                # 保留分隔符
                fixed_parts.append(f' {stripped} ')
            elif stripped:
                # 子查询：检查是否已被括号完整包裹
                if not self._is_wrapped_in_parens(stripped):
                    fixed_parts.append(f'({stripped})')
                else:
                    fixed_parts.append(stripped)

        fixed_sql = ''.join(fixed_parts).strip()
        if fixed_sql != sql.strip():
            logger.info("已自动修复 UNION 语法：为子查询添加括号")
        return fixed_sql

    def _normalize_db_type(self, raw_db_type: Optional[str]) -> DatabaseType:
        """将多种数据库类型写法规范化为内部枚举。"""
        normalized = str(raw_db_type or "mysql").strip().lower().replace(" ", "").replace("_", "")
        if normalized in ("mysql",):
            return DatabaseType.MYSQL
        if normalized in ("sqlserver", "mssql"):
            return DatabaseType.SQLSERVER
        if normalized in ("postgresql", "postgres", "pgsql"):
            return DatabaseType.POSTGRESQL
        raise SQLExecutionError(f"不支持的数据库类型: {raw_db_type}")

    def _normalize_sql_for_db(self, sql: str, db_type: DatabaseType) -> str:
        """按数据库类型做轻量 SQL 方言兼容处理。"""
        normalized_sql = sql.strip()

        # SQL Server 不支持 LIMIT，自动转换常见形式：
        # 1) ... LIMIT n            -> SELECT TOP n ...
        # 2) ... LIMIT n OFFSET m   -> ... OFFSET m ROWS FETCH NEXT n ROWS ONLY
        if db_type == DatabaseType.SQLSERVER:
            limit_offset_pattern = re.compile(r"\s+LIMIT\s+(\d+)\s+OFFSET\s+(\d+)\s*;?\s*$", re.IGNORECASE)
            limit_only_pattern = re.compile(r"\s+LIMIT\s+(\d+)\s*;?\s*$", re.IGNORECASE)

            match_limit_offset = limit_offset_pattern.search(normalized_sql)
            if match_limit_offset:
                limit_value = match_limit_offset.group(1)
                offset_value = match_limit_offset.group(2)
                normalized_sql = limit_offset_pattern.sub(
                    f" OFFSET {offset_value} ROWS FETCH NEXT {limit_value} ROWS ONLY",
                    normalized_sql
                )
                if "ORDER BY" not in normalized_sql.upper():
                    normalized_sql += " ORDER BY (SELECT NULL)"
                logger.info("检测到 SQL Server + LIMIT/OFFSET，已自动转换为 OFFSET FETCH")
                return normalized_sql

            match_limit_only = limit_only_pattern.search(normalized_sql)
            if match_limit_only:
                limit_value = match_limit_only.group(1)
                normalized_sql = limit_only_pattern.sub("", normalized_sql).strip().rstrip(";")
                if re.match(r"^\s*SELECT\s", normalized_sql, re.IGNORECASE):
                    normalized_sql = re.sub(
                        r"^\s*SELECT\s+",
                        f"SELECT TOP {limit_value} ",
                        normalized_sql,
                        count=1,
                        flags=re.IGNORECASE
                    )
                    logger.info("检测到 SQL Server + LIMIT，已自动转换为 TOP")
        return normalized_sql

    def _is_wrapped_in_parens(self, sql: str) -> bool:
        """判断 SQL 是否被一对括号完整包裹"""
        if not (sql.startswith('(') and sql.endswith(')')):
            return False
        # 验证第一个 '(' 对应的 ')' 确实是最后一个字符
        depth = 0
        for i, ch in enumerate(sql):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            if depth == 0:
                return i == len(sql) - 1
        return False

    async def execute_query(
        self,
        sql: str,
        data_source_config: Dict[str, Any],
        use_cache: bool = True,
        stream: bool = False
    ) -> QueryResult:
        """
        执行SQL查询
        
        Args:
            sql: SQL查询语句
            data_source_config: 数据源配置
            use_cache: 是否使用缓存
            stream: 是否使用流式返回
            
        Returns:
            QueryResult: 查询结果
        """
        start_time = time.time()

        data_source_config = dict(data_source_config)
        # 根据数据库类型做方言标准化（必须在缓存前，保证缓存键一致）
        db_type = self._normalize_db_type(data_source_config.get('type', 'mysql'))
        if db_type == DatabaseType.MYSQL:
            data_source_config = remap_mysql_datasource_host(data_source_config)
        sql = self._normalize_sql_for_db(sql, db_type)
        
        # 检查缓存
        if use_cache:
            cache_key = self._generate_cache_key(sql, data_source_config)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.info(f"使用缓存结果: {cache_key}")
                self.stats.cache_hits += 1
                return cached_result
        
        # 并发控制
        async with self._semaphore:
            self._active_queries += 1
            self.stats.total_queries += 1
            
            try:
                logger.info(f"开始执行SQL查询: {sql[:100]}...")
                
                # 预处理 SQL：修复 UNION/UNION ALL 缺少括号的问题
                sql = self._fix_union_syntax(sql)
                
                if stream and self.config.enable_streaming:
                    # 流式执行（暂不实现，返回普通结果）
                    result = await self._execute_with_timeout(sql, data_source_config, db_type)
                else:
                    # 普通执行
                    result = await self._execute_with_timeout(sql, data_source_config, db_type)
                
                # 更新统计信息
                self.stats.successful_queries += 1
                self.stats.total_rows_returned += result.row_count
                self._update_avg_execution_time(result.execution_time)
                
                # 缓存结果
                if use_cache:
                    self._put_to_cache(cache_key, result)
                
                logger.info(f"SQL查询完成，返回 {result.row_count} 行，耗时: {result.execution_time:.2f}s")
                return result
                
            except asyncio.TimeoutError:
                self.stats.timeout_queries += 1
                self.stats.failed_queries += 1
                logger.error(f"SQL查询超时: {self.config.timeout_seconds}秒")
                raise SQLExecutionError(
                    f"查询超时（{self.config.timeout_seconds}秒）",
                    error_code="TIMEOUT"
                )
            except Exception as e:
                self.stats.failed_queries += 1
                logger.error(f"SQL查询失败: {str(e)}", exc_info=True)
                raise SQLExecutionError(
                    f"查询执行失败: {str(e)}",
                    error_code="EXECUTION_ERROR",
                    original_error=e
                )
            finally:
                self._active_queries -= 1
    
    async def _execute_with_timeout(
        self,
        sql: str,
        data_source_config: Dict[str, Any],
        db_type: DatabaseType
    ) -> QueryResult:
        """带超时的执行"""
        try:
            result = await asyncio.wait_for(
                self._execute_query_internal(sql, data_source_config, db_type),
                timeout=self.config.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"查询超时: {sql[:100]}...")
            raise
    
    async def _execute_query_internal(
        self,
        sql: str,
        data_source_config: Dict[str, Any],
        db_type: DatabaseType
    ) -> QueryResult:
        """内部查询执行"""
        start_time = time.time()
        
        # 根据数据库类型执行查询
        if db_type == DatabaseType.MYSQL:
            result = await self._execute_mysql(sql, data_source_config)
        elif db_type == DatabaseType.SQLSERVER:
            result = await self._execute_sqlserver(sql, data_source_config)
        elif db_type == DatabaseType.POSTGRESQL:
            result = await self._execute_postgresql(sql, data_source_config)
        else:
            raise SQLExecutionError(f"不支持的数据库类型: {db_type}")
        
        execution_time = time.time() - start_time
        result.execution_time = execution_time
        
        return result
    
    async def _execute_mysql(
        self,
        sql: str,
        config: Dict[str, Any]
    ) -> QueryResult:
        """执行MySQL查询"""
        connection = None
        try:
            # 在线程池中执行同步数据库操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_mysql_sync,
                sql,
                config
            )
            return result
        except Exception as e:
            logger.error(f"MySQL查询失败: {str(e)}")
            raise SQLExecutionError(
                f"MySQL查询失败: {str(e)}",
                error_code="MYSQL_ERROR",
                original_error=e
            )
    
    def _convert_value_to_json_serializable(self, value):
        """将数据库值转换为 JSON 可序列化的类型"""
        from decimal import Decimal
        from datetime import datetime, date, time
        
        if value is None:
            return None
        elif isinstance(value, Decimal):
            # 将 Decimal 转换为 float
            return float(value)
        elif isinstance(value, (datetime, date, time)):
            # 将日期时间转换为字符串
            return value.isoformat()
        elif isinstance(value, bytes):
            # 将字节转换为字符串
            try:
                return value.decode('utf-8')
            except:
                return str(value)
        else:
            return value
    
    def _execute_mysql_sync(
        self,
        sql: str,
        config: Dict[str, Any]
    ) -> QueryResult:
        """同步执行MySQL查询"""
        if not PYMYSQL_AVAILABLE:
            raise SQLExecutionError(
                "pymysql not installed, MySQL support disabled",
                error_code="DRIVER_NOT_AVAILABLE"
            )
        
        connection = None
        try:
            # 建立连接
            connection = pymysql.connect(
                host=config.get('host', 'localhost'),
                port=config.get('port', 3306),
                user=config.get('username', 'root'),
                password=config.get('password', ''),
                database=config.get('database', ''),
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            
            with connection.cursor() as cursor:
                # 执行查询
                cursor.execute(sql)
                
                # 获取列名
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # 获取结果（限制行数）
                rows = []
                is_truncated = False
                row_count = 0
                
                for row in cursor:
                    if row_count >= self.config.max_rows:
                        is_truncated = True
                        break
                    
                    # 转换为列表格式，并处理 Decimal 等特殊类型
                    row_list = [self._convert_value_to_json_serializable(row[col]) for col in columns]
                    rows.append(row_list)
                    row_count += 1
                
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=row_count,
                    execution_time=0.0,  # 将在外部设置
                    is_truncated=is_truncated,
                    has_more=is_truncated,
                    metadata={
                        'database_type': 'mysql',
                        'max_rows_limit': self.config.max_rows
                    }
                )
        finally:
            if connection:
                connection.close()
    
    async def _execute_sqlserver(
        self,
        sql: str,
        config: Dict[str, Any]
    ) -> QueryResult:
        """执行SQL Server查询"""
        try:
            # 在线程池中执行同步数据库操作
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_sqlserver_sync,
                sql,
                config
            )
            return result
        except Exception as e:
            logger.error(f"SQL Server查询失败: {str(e)}")
            raise SQLExecutionError(
                f"SQL Server查询失败: {str(e)}",
                error_code="SQLSERVER_ERROR",
                original_error=e
            )
    
    def _execute_sqlserver_sync(
        self,
        sql: str,
        config: Dict[str, Any]
    ) -> QueryResult:
        """同步执行SQL Server查询"""
        if not PYMSSQL_AVAILABLE and not PYODBC_AVAILABLE:
            raise SQLExecutionError(
                "未安装可用 SQL Server 驱动（pymssql/pyodbc）",
                error_code="DRIVER_NOT_AVAILABLE"
            )
        
        connection = None
        cursor = None
        try:
            if PYMSSQL_AVAILABLE:
                # 建立连接（优先使用 pymssql）
                connection = pymssql.connect(
                    server=config.get('host', 'localhost'),
                    port=config.get('port', 1433),
                    user=config.get('username', 'sa'),
                    password=config.get('password', ''),
                    database=config.get('database', ''),
                    timeout=10
                )
                cursor = connection.cursor(as_dict=True)
            else:
                # fallback: 使用 pyodbc（与现有 SQL Server 连接测试逻辑保持一致）
                from src.utils.sql_server_odbc import build_sql_server_connection_string

                conn_str = build_sql_server_connection_string(
                    host=config.get('host', 'localhost'),
                    database_name=config.get('database', ''),
                    username=config.get('username') or '',
                    password=config.get('password') or '',
                    port=config.get('port', 1433),
                    domain=config.get('domain')
                )
                connection = pyodbc.connect(conn_str, timeout=10)
                cursor = connection.cursor()
            
            # 执行查询
            cursor.execute(sql)
            
            # 获取列名
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # 获取结果（限制行数）
            rows = []
            is_truncated = False
            row_count = 0
            
            for row in cursor:
                if row_count >= self.config.max_rows:
                    is_truncated = True
                    break

                # 转换为列表格式
                if isinstance(row, dict):
                    row_list = [self._convert_value_to_json_serializable(row.get(col)) for col in columns]
                else:
                    row_list = [self._convert_value_to_json_serializable(row[i]) for i in range(len(columns))]
                rows.append(row_list)
                row_count += 1
            
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=row_count,
                execution_time=0.0,  # 将在外部设置
                is_truncated=is_truncated,
                has_more=is_truncated,
                metadata={
                    'database_type': 'sqlserver',
                    'max_rows_limit': self.config.max_rows
                }
            )
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
    
    async def _execute_postgresql(
        self,
        sql: str,
        config: Dict[str, Any]
    ) -> QueryResult:
        """执行PostgreSQL查询"""
        # TODO: 实现PostgreSQL支持
        raise SQLExecutionError(
            "PostgreSQL支持尚未实现",
            error_code="NOT_IMPLEMENTED"
        )
    
    async def execute_query_paginated(
        self,
        sql: str,
        data_source_config: Dict[str, Any],
        page: int = 1,
        page_size: int = None
    ) -> QueryResult:
        """
        分页执行查询
        
        Args:
            sql: SQL查询语句
            data_source_config: 数据源配置
            page: 页码（从1开始）
            page_size: 每页大小
            
        Returns:
            QueryResult: 查询结果（包含分页信息）
        """
        page_size = page_size or self.config.page_size
        offset = (page - 1) * page_size
        
        # 修改SQL添加分页
        db_type = self._normalize_db_type(data_source_config.get('type', 'mysql'))
        paginated_sql = self._add_pagination_to_sql(sql, offset, page_size, db_type)
        
        # 执行查询
        result = await self.execute_query(paginated_sql, data_source_config, use_cache=False)
        
        # 添加分页信息
        result.page_info = {
            'page': page,
            'page_size': page_size,
            'offset': offset,
            'has_next': result.row_count == page_size
        }
        
        return result
    
    def _add_pagination_to_sql(
        self,
        sql: str,
        offset: int,
        limit: int,
        db_type: DatabaseType
    ) -> str:
        """为SQL添加分页"""
        sql = sql.rstrip(';').strip()
        
        if db_type == DatabaseType.MYSQL or db_type == DatabaseType.POSTGRESQL:
            return f"{sql} LIMIT {limit} OFFSET {offset};"
        elif db_type == DatabaseType.SQLSERVER:
            # SQL Server使用OFFSET FETCH
            if 'ORDER BY' not in sql.upper():
                # 如果没有ORDER BY，添加一个默认的
                sql += " ORDER BY (SELECT NULL)"
            return f"{sql} OFFSET {offset} ROWS FETCH NEXT {limit} ROWS ONLY;"
        else:
            return sql
    
    async def execute_query_stream(
        self,
        sql: str,
        data_source_config: Dict[str, Any],
        chunk_size: int = 100
    ) -> AsyncIterator[List[List[Any]]]:
        """
        流式执行查询
        
        Args:
            sql: SQL查询语句
            data_source_config: 数据源配置
            chunk_size: 每次返回的行数
            
        Yields:
            List[List[Any]]: 数据块
        """
        # 简化实现：分页获取并流式返回
        page = 1
        while True:
            result = await self.execute_query_paginated(
                sql,
                data_source_config,
                page=page,
                page_size=chunk_size
            )
            
            if result.row_count == 0:
                break
            
            yield result.rows
            
            if not result.page_info.get('has_next', False):
                break
            
            page += 1
    
    def format_result_for_display(
        self,
        result: QueryResult,
        format_type: str = 'json'
    ) -> Any:
        """
        格式化结果用于显示
        
        Args:
            result: 查询结果
            format_type: 格式类型 (json, csv, table)
            
        Returns:
            格式化后的结果
        """
        if format_type == 'json':
            return {
                'columns': result.columns,
                'data': result.rows,
                'row_count': result.row_count,
                'execution_time': result.execution_time,
                'is_truncated': result.is_truncated,
                'has_more': result.has_more,
                'page_info': result.page_info,
                'metadata': result.metadata
            }
        elif format_type == 'csv':
            return self._format_as_csv(result)
        elif format_type == 'table':
            return self._format_as_table(result)
        else:
            raise ValueError(f"不支持的格式类型: {format_type}")
    
    def _format_as_csv(self, result: QueryResult) -> str:
        """格式化为CSV"""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入列名
        writer.writerow(result.columns)
        
        # 写入数据
        for row in result.rows:
            writer.writerow(row)
        
        return output.getvalue()
    
    def _format_as_table(self, result: QueryResult) -> str:
        """格式化为表格"""
        if not result.columns or not result.rows:
            return "无数据"
        
        # 计算列宽
        col_widths = [len(col) for col in result.columns]
        for row in result.rows:
            for i, cell in enumerate(row):
                cell_str = str(cell) if cell is not None else 'NULL'
                col_widths[i] = max(col_widths[i], len(cell_str))
        
        # 构建表格
        lines = []
        
        # 表头
        header = ' | '.join(col.ljust(col_widths[i]) for i, col in enumerate(result.columns))
        lines.append(header)
        lines.append('-' * len(header))
        
        # 数据行
        for row in result.rows[:100]:  # 最多显示100行
            row_str = ' | '.join(
                str(cell).ljust(col_widths[i]) if cell is not None else 'NULL'.ljust(col_widths[i])
                for i, cell in enumerate(row)
            )
            lines.append(row_str)
        
        if result.row_count > 100:
            lines.append(f"... ({result.row_count - 100} more rows)")
        
        return '\n'.join(lines)
    
    def _generate_cache_key(self, sql: str, config: Dict[str, Any]) -> str:
        """生成缓存键"""
        import hashlib
        
        key_str = f"{sql}_{config.get('host')}_{config.get('database')}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[QueryResult]:
        """从缓存获取结果"""
        if cache_key not in self._result_cache:
            return None
        
        # 检查是否过期
        timestamp = self._cache_timestamps.get(cache_key, 0)
        if time.time() - timestamp > self._cache_ttl:
            # 过期，删除缓存
            del self._result_cache[cache_key]
            del self._cache_timestamps[cache_key]
            return None
        
        return self._result_cache[cache_key]
    
    def _put_to_cache(self, cache_key: str, result: QueryResult):
        """将结果放入缓存"""
        self._result_cache[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()
        
        # 简单的缓存清理：如果缓存过大，删除最旧的
        if len(self._result_cache) > 100:
            oldest_key = min(self._cache_timestamps, key=self._cache_timestamps.get)
            del self._result_cache[oldest_key]
            del self._cache_timestamps[oldest_key]
    
    def _update_avg_execution_time(self, execution_time: float):
        """更新平均执行时间"""
        if self.stats.successful_queries == 1:
            self.stats.average_execution_time = execution_time
        else:
            total_time = (
                self.stats.average_execution_time * (self.stats.successful_queries - 1) +
                execution_time
            )
            self.stats.average_execution_time = total_time / self.stats.successful_queries
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            'total_queries': self.stats.total_queries,
            'successful_queries': self.stats.successful_queries,
            'failed_queries': self.stats.failed_queries,
            'timeout_queries': self.stats.timeout_queries,
            'success_rate': (
                self.stats.successful_queries / max(self.stats.total_queries, 1)
            ),
            'average_execution_time': self.stats.average_execution_time,
            'total_rows_returned': self.stats.total_rows_returned,
            'cache_hits': self.stats.cache_hits,
            'cache_hit_rate': (
                self.stats.cache_hits / max(self.stats.total_queries, 1)
            ),
            'active_queries': self._active_queries,
            'cache_size': len(self._result_cache)
        }
    
    def clear_cache(self):
        """清空缓存"""
        self._result_cache.clear()
        self._cache_timestamps.clear()
        logger.info("查询结果缓存已清空")
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            'status': 'healthy' if self.stats.failed_queries < self.stats.successful_queries else 'degraded',
            'active_queries': self._active_queries,
            'max_concurrent_queries': self.config.max_concurrent_queries,
            'cache_size': len(self._result_cache),
            'statistics': self.get_statistics()
        }
