"""
SQL执行API单元测试

测试SQL执行API端点的功能
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from src.main import app
from src.services.sql_executor_service import (
    SQLExecutorService,
    QueryResult,
    ExecutionConfig,
    SQLExecutionError
)


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_executor():
    """创建Mock执行服务"""
    executor = Mock(spec=SQLExecutorService)
    executor.config = ExecutionConfig()
    executor.stats = Mock()
    executor.stats.total_queries = 10
    executor.stats.successful_queries = 8
    executor.stats.failed_queries = 2
    executor.stats.timeout_queries = 0
    executor.stats.average_execution_time = 1.5
    executor.stats.total_rows_returned = 1000
    executor.stats.cache_hits = 5
    return executor


class TestSQLExecutorAPI:
    """SQL执行API测试"""
    
    def test_execute_query_success(self, client, mock_executor):
        """测试SQL执行成功"""
        # Mock查询结果
        mock_result = QueryResult(
            columns=['id', 'name', 'email'],
            rows=[[1, 'Alice', 'alice@example.com'], [2, 'Bob', 'bob@example.com']],
            row_count=2,
            execution_time=0.5,
            is_truncated=False,
            has_more=False,
            metadata={'database_type': 'mysql'}
        )
        
        mock_executor.execute_query = AsyncMock(return_value=mock_result)
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute',
                json={
                    'sql': 'SELECT * FROM users LIMIT 10;',
                    'data_source_id': 1,
                    'use_cache': True
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['row_count'] == 2
            assert len(data['columns']) == 3
            assert data['columns'] == ['id', 'name', 'email']
            assert len(data['rows']) == 2
            assert data['execution_time'] == 0.5
    
    def test_execute_query_with_timeout(self, client, mock_executor):
        """测试带超时的SQL执行"""
        mock_result = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time=0.5,
            metadata={'database_type': 'mysql'}
        )
        
        mock_executor.execute_query = AsyncMock(return_value=mock_result)
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute',
                json={
                    'sql': 'SELECT * FROM users;',
                    'data_source_id': 1,
                    'timeout_seconds': 60,
                    'max_rows': 5000
                }
            )
            
            assert response.status_code == 200
            assert mock_executor.config.timeout_seconds == 60
            assert mock_executor.config.max_rows == 5000
    
    def test_execute_query_validation_error(self, client):
        """测试SQL验证错误"""
        response = client.post(
            '/api/sql-executor/execute',
            json={
                'sql': '',  # 空SQL
                'data_source_id': 1
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_execute_query_execution_error(self, client, mock_executor):
        """测试SQL执行错误"""
        mock_executor.execute_query = AsyncMock(
            side_effect=SQLExecutionError("Table not found", error_code="TABLE_NOT_FOUND")
        )
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute',
                json={
                    'sql': 'SELECT * FROM non_existent;',
                    'data_source_id': 1
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert 'detail' in data
            assert data['detail']['error_code'] == 'TABLE_NOT_FOUND'
    
    def test_execute_query_paginated(self, client, mock_executor):
        """测试分页查询"""
        mock_result = QueryResult(
            columns=['id', 'name'],
            rows=[[i, f'User{i}'] for i in range(1, 11)],
            row_count=10,
            execution_time=0.5,
            page_info={
                'page': 1,
                'page_size': 10,
                'offset': 0,
                'has_next': True
            },
            metadata={'database_type': 'mysql'}
        )
        
        mock_executor.execute_query_paginated = AsyncMock(return_value=mock_result)
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute/paginated',
                json={
                    'sql': 'SELECT * FROM users;',
                    'data_source_id': 1,
                    'page': 1,
                    'page_size': 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['row_count'] == 10
            assert data['page_info']['page'] == 1
            assert data['page_info']['page_size'] == 10
            assert data['page_info']['has_next'] is True
    
    def test_execute_batch_queries(self, client, mock_executor):
        """测试批量查询"""
        mock_result1 = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time=0.3,
            metadata={'database_type': 'mysql'}
        )
        
        mock_result2 = QueryResult(
            columns=['id'],
            rows=[[2]],
            row_count=1,
            execution_time=0.4,
            metadata={'database_type': 'mysql'}
        )
        
        mock_executor.execute_query = AsyncMock(side_effect=[mock_result1, mock_result2])
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute/batch',
                json={
                    'queries': [
                        {
                            'sql': 'SELECT * FROM users WHERE id=1;',
                            'data_source_id': 1,
                            'use_cache': False
                        },
                        {
                            'sql': 'SELECT * FROM users WHERE id=2;',
                            'data_source_id': 1,
                            'use_cache': False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data['results']) == 2
            assert data['successful_count'] == 2
            assert data['failed_count'] == 0
            assert data['total_execution_time'] > 0
    
    def test_execute_batch_queries_with_failures(self, client, mock_executor):
        """测试批量查询包含失败"""
        mock_result = QueryResult(
            columns=['id'],
            rows=[[1]],
            row_count=1,
            execution_time=0.3,
            metadata={'database_type': 'mysql'}
        )
        
        mock_executor.execute_query = AsyncMock(
            side_effect=[mock_result, Exception("Query failed")]
        )
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/execute/batch',
                json={
                    'queries': [
                        {
                            'sql': 'SELECT * FROM users WHERE id=1;',
                            'data_source_id': 1,
                            'use_cache': False
                        },
                        {
                            'sql': 'SELECT * FROM invalid;',
                            'data_source_id': 1,
                            'use_cache': False
                        }
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['successful_count'] == 1
            assert data['failed_count'] == 1
            assert data['results'][1]['metadata']['error'] is not None
    
    def test_get_statistics(self, client, mock_executor):
        """测试获取统计信息"""
        mock_executor.get_statistics = Mock(return_value={
            'total_queries': 10,
            'successful_queries': 8,
            'failed_queries': 2,
            'timeout_queries': 0,
            'success_rate': 0.8,
            'average_execution_time': 1.5,
            'total_rows_returned': 1000,
            'cache_hits': 5,
            'cache_hit_rate': 0.5,
            'active_queries': 0,
            'cache_size': 10
        })
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.get('/api/sql-executor/statistics')
            
            assert response.status_code == 200
            data = response.json()
            assert data['total_queries'] == 10
            assert data['successful_queries'] == 8
            assert data['success_rate'] == 0.8
            assert data['average_execution_time'] == 1.5
            assert data['cache_hit_rate'] == 0.5
    
    def test_get_health_status(self, client, mock_executor):
        """测试获取健康状态"""
        mock_executor.get_health_status = Mock(return_value={
            'status': 'healthy',
            'active_queries': 2,
            'max_concurrent_queries': 10,
            'cache_size': 15,
            'statistics': {
                'total_queries': 10,
                'successful_queries': 8,
                'failed_queries': 2,
                'timeout_queries': 0,
                'success_rate': 0.8,
                'average_execution_time': 1.5,
                'total_rows_returned': 1000,
                'cache_hits': 5,
                'cache_hit_rate': 0.5,
                'active_queries': 2,
                'cache_size': 15
            }
        })
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.get('/api/sql-executor/health')
            
            assert response.status_code == 200
            data = response.json()
            assert data['status'] == 'healthy'
            assert data['active_queries'] == 2
            assert data['max_concurrent_queries'] == 10
            assert 'statistics' in data
    
    def test_clear_cache(self, client, mock_executor):
        """测试清空缓存"""
        mock_executor.clear_cache = Mock()
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post('/api/sql-executor/cache/clear')
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert '缓存已清空' in data['message']
            mock_executor.clear_cache.assert_called_once()
    
    def test_format_result_json(self, client, mock_executor):
        """测试JSON格式化"""
        mock_executor.format_result_for_display = Mock(return_value={
            'columns': ['id', 'name'],
            'data': [[1, 'Alice'], [2, 'Bob']],
            'row_count': 2
        })
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/format',
                json={
                    'result': {
                        'columns': ['id', 'name'],
                        'rows': [[1, 'Alice'], [2, 'Bob']],
                        'row_count': 2,
                        'execution_time': 0.5,
                        'is_truncated': False,
                        'has_more': False
                    },
                    'format_request': {
                        'format_type': 'json'
                    }
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['format_type'] == 'json'
            assert 'formatted_result' in data
    
    def test_format_result_csv(self, client, mock_executor):
        """测试CSV格式化"""
        mock_executor.format_result_for_display = Mock(return_value="id,name\n1,Alice\n2,Bob\n")
        
        with patch('src.api.sql_executor_api.get_executor_service', return_value=mock_executor):
            response = client.post(
                '/api/sql-executor/format',
                json={
                    'result': {
                        'columns': ['id', 'name'],
                        'rows': [[1, 'Alice'], [2, 'Bob']],
                        'row_count': 2,
                        'execution_time': 0.5,
                        'is_truncated': False,
                        'has_more': False
                    },
                    'format_request': {
                        'format_type': 'csv'
                    }
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['format_type'] == 'csv'
            assert 'id,name' in data['formatted_result']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
