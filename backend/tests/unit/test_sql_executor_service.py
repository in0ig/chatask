"""
SQL执行服务单元测试

测试SQL执行、分页查询、流式查询、结果格式化等功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.services.sql_executor_service import (
    SQLExecutorService,
    ExecutionConfig,
    QueryResult,
    DatabaseType,
    SQLExecutionError
)


@pytest.fixture
def executor_service():
    """创建SQL执行服务实例"""
    config = ExecutionConfig(
        timeout_seconds=30,
        max_rows=10000,
        max_memory_mb=100,
        enable_streaming=True,
        page_size=1000,
        max_concurrent_queries=10
    )
    return SQLExecutorService(config)


@pytest.fixture
def mysql_config():
    """MySQL数据源配置"""
    return {
        'type': 'mysql',
        'host': 'localhost',
        'port': 3306,
        'username': 'root',
        'password': 'password',
        'database': 'test_db'
    }


@pytest.fixture
def sqlserver_config():
    """SQL Server数据源配置"""
    return {
        'type': 'sqlserver',
        'host': 'localhost',
        'port': 1433,
        'username': 'sa',
        'password': 'password',
        'database': 'test_db'
    }


class TestSQLExecutorService:
    """SQL执行服务测试"""
    
    @pytest.mark.asyncio
    async def test_execute_query_mysql_success(self, executor_service, mysql_config):
        """测试MySQL查询成功执行"""
        sql = "SELECT * FROM users LIMIT 10;"
        
        # Mock MySQL执行
        mock_result = QueryResult(
            columns=['id', 'name', 'email'],
            rows=[[1, 'Alice', 'alice@example.com'], [2, 'Bob', 'bob@example.com']],
            row_count=2,
            execution_time=0.5,
            is_truncated=False,
            has_more=False,
            metadata={'database_type': 'mysql'}
        )
        
        with patch.object(executor_service, '_execute_mysql', return_value=mock_result):
            result = await executor_service.execute_query(sql, mysql_config, use_cache=False)
            
            assert result.row_count == 2
            assert len(result.columns) == 3
            assert result.columns == ['id', 'name', 'email']
            assert result.is_truncated is False
            assert result.metadata['database_type'] == 'mysql'
    
    @pytest.mark.asyncio
    async def test_execute_query_with_cache(self, executor_service, mysql_config):
        """测试查询结果缓存"""
        sql = "SELECT * FROM users LIMIT 10;"
        
        mock_result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice']],
            row_count=1,
            execution_time=0.5,
            metadata={'database_type': 'mysql'}
        )
        
        with patch.object(executor_service, '_execute_mysql', return_value=mock_result) as mock_execute:
            # 第一次执行
            result1 = await executor_service.execute_query(sql, mysql_config, use_cache=True)
            assert mock_execute.call_count == 1
            
            # 第二次执行（应该使用缓存）
            result2 = await executor_service.execute_query(sql, mysql_config, use_cache=True)
            assert mock_execute.call_count == 1  # 没有再次调用
            assert result2.row_count == result1.row_count
            assert executor_service.stats.cache_hits == 1
    
    @pytest.mark.asyncio
    async def test_execute_query_timeout(self, executor_service, mysql_config):
        """测试查询超时"""
        sql = "SELECT * FROM large_table;"
        
        # Mock一个会超时的查询
        async def slow_query(*args, **kwargs):
            await asyncio.sleep(100)  # 模拟慢查询
            return QueryResult(columns=[], rows=[], row_count=0, execution_time=100)
        
        with patch.object(executor_service, '_execute_query_internal', side_effect=slow_query):
            executor_service.config.timeout_seconds = 1  # 设置1秒超时
            
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor_service.execute_query(sql, mysql_config, use_cache=False)
            
            assert exc_info.value.error_code == "TIMEOUT"
            assert executor_service.stats.timeout_queries == 1
    
    @pytest.mark.asyncio
    async def test_execute_query_truncated(self, executor_service, mysql_config):
        """测试结果截断"""
        sql = "SELECT * FROM users;"
        
        # 创建超过max_rows的结果
        executor_service.config.max_rows = 5
        
        mock_result = QueryResult(
            columns=['id', 'name'],
            rows=[[i, f'User{i}'] for i in range(5)],
            row_count=5,
            execution_time=0.5,
            is_truncated=True,
            has_more=True,
            metadata={'database_type': 'mysql', 'max_rows_limit': 5}
        )
        
        with patch.object(executor_service, '_execute_mysql', return_value=mock_result):
            result = await executor_service.execute_query(sql, mysql_config, use_cache=False)
            
            assert result.is_truncated is True
            assert result.has_more is True
            assert result.row_count == 5
    
    @pytest.mark.asyncio
    async def test_execute_query_paginated(self, executor_service, mysql_config):
        """测试分页查询"""
        sql = "SELECT * FROM users;"
        
        mock_result = QueryResult(
            columns=['id', 'name'],
            rows=[[i, f'User{i}'] for i in range(1, 11)],
            row_count=10,
            execution_time=0.5,
            metadata={'database_type': 'mysql'}
        )
        
        with patch.object(executor_service, 'execute_query', return_value=mock_result):
            result = await executor_service.execute_query_paginated(
                sql, mysql_config, page=1, page_size=10
            )
            
            assert result.page_info is not None
            assert result.page_info['page'] == 1
            assert result.page_info['page_size'] == 10
            assert result.page_info['offset'] == 0
    
    @pytest.mark.asyncio
    async def test_execute_query_stream(self, executor_service, mysql_config):
        """测试流式查询"""
        sql = "SELECT * FROM users;"
        
        # Mock分页结果
        async def mock_paginated(sql, config, page, page_size):
            if page == 1:
                return QueryResult(
                    columns=['id', 'name'],
                    rows=[[1, 'Alice'], [2, 'Bob']],
                    row_count=2,
                    execution_time=0.5,
                    page_info={'page': 1, 'page_size': 2, 'has_next': True}
                )
            elif page == 2:
                return QueryResult(
                    columns=['id', 'name'],
                    rows=[[3, 'Charlie']],
                    row_count=1,
                    execution_time=0.5,
                    page_info={'page': 2, 'page_size': 2, 'has_next': False}
                )
            else:
                return QueryResult(
                    columns=['id', 'name'],
                    rows=[],
                    row_count=0,
                    execution_time=0.5,
                    page_info={'page': page, 'page_size': 2, 'has_next': False}
                )
        
        with patch.object(executor_service, 'execute_query_paginated', side_effect=mock_paginated):
            chunks = []
            async for chunk in executor_service.execute_query_stream(sql, mysql_config, chunk_size=2):
                chunks.append(chunk)
            
            assert len(chunks) == 2
            assert len(chunks[0]) == 2  # 第一页2行
            assert len(chunks[1]) == 1  # 第二页1行
    
    def test_add_pagination_to_sql_mysql(self, executor_service):
        """测试MySQL分页SQL生成"""
        sql = "SELECT * FROM users"
        paginated = executor_service._add_pagination_to_sql(
            sql, offset=10, limit=20, db_type=DatabaseType.MYSQL
        )
        
        assert "LIMIT 20 OFFSET 10" in paginated
        assert paginated.endswith(";")
    
    def test_add_pagination_to_sql_sqlserver(self, executor_service):
        """测试SQL Server分页SQL生成"""
        sql = "SELECT * FROM users ORDER BY id"
        paginated = executor_service._add_pagination_to_sql(
            sql, offset=10, limit=20, db_type=DatabaseType.SQLSERVER
        )
        
        assert "OFFSET 10 ROWS FETCH NEXT 20 ROWS ONLY" in paginated
    
    def test_format_result_json(self, executor_service):
        """测试JSON格式化"""
        result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice'], [2, 'Bob']],
            row_count=2,
            execution_time=0.5,
            metadata={'database_type': 'mysql'}
        )
        
        formatted = executor_service.format_result_for_display(result, format_type='json')
        
        assert formatted['columns'] == ['id', 'name']
        assert len(formatted['data']) == 2
        assert formatted['row_count'] == 2
        assert formatted['execution_time'] == 0.5
    
    def test_format_result_csv(self, executor_service):
        """测试CSV格式化"""
        result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice'], [2, 'Bob']],
            row_count=2,
            execution_time=0.5
        )
        
        formatted = executor_service.format_result_for_display(result, format_type='csv')
        
        assert 'id,name' in formatted
        assert '1,Alice' in formatted
        assert '2,Bob' in formatted
    
    def test_format_result_table(self, executor_service):
        """测试表格格式化"""
        result = QueryResult(
            columns=['id', 'name'],
            rows=[[1, 'Alice'], [2, 'Bob']],
            row_count=2,
            execution_time=0.5
        )
        
        formatted = executor_service.format_result_for_display(result, format_type='table')
        
        assert 'id' in formatted
        assert 'name' in formatted
        assert 'Alice' in formatted
        assert 'Bob' in formatted
        assert '|' in formatted  # 表格分隔符
    
    def test_cache_key_generation(self, executor_service, mysql_config):
        """测试缓存键生成"""
        sql1 = "SELECT * FROM users;"
        sql2 = "SELECT * FROM orders;"
        
        key1 = executor_service._generate_cache_key(sql1, mysql_config)
        key2 = executor_service._generate_cache_key(sql2, mysql_config)
        key3 = executor_service._generate_cache_key(sql1, mysql_config)
        
        assert key1 != key2  # 不同SQL应该有不同的键
        assert key1 == key3  # 相同SQL应该有相同的键
    
    def test_cache_expiration(self, executor_service, mysql_config):
        """测试缓存过期"""
        import time
        
        sql = "SELECT * FROM users;"
        cache_key = executor_service._generate_cache_key(sql, mysql_config)
        
        result = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time=0.5
        )
        
        # 放入缓存
        executor_service._put_to_cache(cache_key, result)
        
        # 立即获取应该成功
        cached = executor_service._get_from_cache(cache_key)
        assert cached is not None
        
        # 修改缓存时间戳使其过期
        executor_service._cache_timestamps[cache_key] = time.time() - 400  # 400秒前
        
        # 获取过期缓存应该返回None
        cached = executor_service._get_from_cache(cache_key)
        assert cached is None
    
    def test_clear_cache(self, executor_service, mysql_config):
        """测试清空缓存"""
        sql = "SELECT * FROM users;"
        cache_key = executor_service._generate_cache_key(sql, mysql_config)
        
        result = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time=0.5
        )
        
        executor_service._put_to_cache(cache_key, result)
        assert len(executor_service._result_cache) == 1
        
        executor_service.clear_cache()
        assert len(executor_service._result_cache) == 0
        assert len(executor_service._cache_timestamps) == 0
    
    def test_statistics_tracking(self, executor_service):
        """测试统计信息跟踪"""
        # 初始统计
        stats = executor_service.get_statistics()
        assert stats['total_queries'] == 0
        assert stats['successful_queries'] == 0
        assert stats['failed_queries'] == 0
        
        # 更新统计
        executor_service.stats.total_queries = 10
        executor_service.stats.successful_queries = 8
        executor_service.stats.failed_queries = 2
        executor_service.stats.average_execution_time = 1.5
        
        stats = executor_service.get_statistics()
        assert stats['total_queries'] == 10
        assert stats['success_rate'] == 0.8
        assert stats['average_execution_time'] == 1.5
    
    def test_health_status(self, executor_service):
        """测试健康状态"""
        # 健康状态
        executor_service.stats.successful_queries = 10
        executor_service.stats.failed_queries = 1
        
        health = executor_service.get_health_status()
        assert health['status'] == 'healthy'
        assert 'statistics' in health
        
        # 降级状态
        executor_service.stats.failed_queries = 15
        
        health = executor_service.get_health_status()
        assert health['status'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_concurrent_query_limit(self, executor_service, mysql_config):
        """测试并发查询限制"""
        executor_service.config.max_concurrent_queries = 2
        executor_service._semaphore = asyncio.Semaphore(2)
        
        sql = "SELECT * FROM users;"
        
        async def slow_query(*args, **kwargs):
            await asyncio.sleep(0.1)
            return QueryResult(
                columns=['id'],
                rows=[[1]],
                row_count=1,
                execution_time=0.1
            )
        
        with patch.object(executor_service, '_execute_mysql', side_effect=slow_query):
            # 启动3个并发查询
            tasks = [
                executor_service.execute_query(sql, mysql_config, use_cache=False)
                for _ in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 3
            assert all(r.row_count == 1 for r in results)
    
    @pytest.mark.asyncio
    async def test_execution_error_handling(self, executor_service, mysql_config):
        """测试执行错误处理"""
        sql = "SELECT * FROM non_existent_table;"
        
        with patch.object(executor_service, '_execute_mysql', side_effect=Exception("Table not found")):
            with pytest.raises(SQLExecutionError) as exc_info:
                await executor_service.execute_query(sql, mysql_config, use_cache=False)
            
            assert exc_info.value.error_code == "EXECUTION_ERROR"
            assert "Table not found" in str(exc_info.value)
            assert executor_service.stats.failed_queries == 1
    
    def test_update_avg_execution_time(self, executor_service):
        """测试平均执行时间更新"""
        # 第一次查询
        executor_service.stats.successful_queries = 1
        executor_service._update_avg_execution_time(1.0)
        assert executor_service.stats.average_execution_time == 1.0
        
        # 第二次查询
        executor_service.stats.successful_queries = 2
        executor_service._update_avg_execution_time(2.0)
        assert executor_service.stats.average_execution_time == 1.5
        
        # 第三次查询
        executor_service.stats.successful_queries = 3
        executor_service._update_avg_execution_time(3.0)
        assert executor_service.stats.average_execution_time == 2.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
