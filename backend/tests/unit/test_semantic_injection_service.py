import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.semantic_injection_service import SemanticInjectionService
from src.models.data_preparation_model import Dictionary, DictionaryItem, FieldMapping, DataTable, TableField

class TestSemanticInjectionService:
    """语义注入服务测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.service = SemanticInjectionService()
        self.mock_db = Mock(spec=Session)
    
    def test_init(self):
        """测试服务初始化"""
        service = SemanticInjectionService()
        assert service._cache == {}
        assert isinstance(service._cache_ttl, timedelta)
        assert isinstance(service._last_cache_clear, datetime)
    
    def test_get_cache_key(self):
        """测试缓存键生成"""
        key = self.service._get_cache_key("users", "status")
        assert key == "users.status"
    
    def test_clear_expired_cache(self):
        """测试清理过期缓存"""
        # 设置缓存
        self.service._cache["test"] = "value"
        
        # 模拟过期时间
        self.service._last_cache_clear = datetime.now() - timedelta(hours=1)
        
        self.service._clear_expired_cache()
        
        assert self.service._cache == {}
    
    def test_get_field_semantic_mapping_not_found(self):
        """测试获取不存在的字段语义映射"""
        # Mock查询返回None
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = self.service.get_field_semantic_mapping(
            self.mock_db, "users", "status"
        )
        
        assert result is None
    
    def test_get_field_semantic_mapping_success(self):
        """测试成功获取字段语义映射"""
        # Mock数据
        mock_table = Mock(spec=DataTable)
        mock_table.table_name = "users"
        
        mock_field = Mock(spec=TableField)
        mock_field.field_name = "status"
        
        mock_field_mapping = Mock(spec=FieldMapping)
        mock_field_mapping.id = "mapping_1"
        mock_field_mapping.dictionary_id = "dict_1"
        mock_field_mapping.table = mock_table
        mock_field_mapping.field = mock_field
        
        mock_dictionary = Mock(spec=Dictionary)
        mock_dictionary.id = "dict_1"
        mock_dictionary.name = "用户状态字典"
        mock_dictionary.code = "USER_STATUS"
        mock_dictionary.description = "用户状态枚举"
        mock_dictionary.created_at = datetime.now()
        mock_dictionary.updated_at = datetime.now()
        
        mock_dict_item1 = Mock(spec=DictionaryItem)
        mock_dict_item1.code = "1"
        mock_dict_item1.name = "激活"
        mock_dict_item1.description = "用户已激活"
        mock_dict_item1.sort_order = 1
        mock_dict_item1.is_active = True
        
        mock_dict_item2 = Mock(spec=DictionaryItem)
        mock_dict_item2.code = "0"
        mock_dict_item2.name = "禁用"
        mock_dict_item2.description = "用户已禁用"
        mock_dict_item2.sort_order = 2
        mock_dict_item2.is_active = True
        
        # Mock查询链 - 模拟复杂的join查询
        query_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock = Mock()
        
        # 第一次查询：字段映射（带join）
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock
        filter_mock.first.return_value = mock_field_mapping
        
        # 第二次查询：字典
        query_mock2 = Mock()
        filter_mock2 = Mock()
        query_mock2.filter.return_value = filter_mock2
        filter_mock2.first.return_value = mock_dictionary
        
        # 第三次查询：字典项
        query_mock3 = Mock()
        filter_mock3 = Mock()
        query_mock3.filter.return_value = filter_mock3
        filter_mock3.all.return_value = [mock_dict_item1, mock_dict_item2]
        
        self.mock_db.query.side_effect = [query_mock, query_mock2, query_mock3]
        
        result = self.service.get_field_semantic_mapping(
            self.mock_db, "users", "status"
        )
        
        assert result is not None
        assert result['dictionary_id'] == "dict_1"
        assert result['dictionary_name'] == "用户状态字典"
        assert result['dictionary_code'] == "USER_STATUS"
        assert result['field_mapping_id'] == "mapping_1"
        assert result['mapping_type'] == "direct"
        assert "1" in result['value_mappings']
        assert "0" in result['value_mappings']
        assert result['value_mappings']['1']['label'] == "激活"
        assert result['value_mappings']['0']['label'] == "禁用"
    
    def test_get_field_semantic_mapping_with_cache(self):
        """测试从缓存获取字段语义映射"""
        # 设置缓存
        cache_key = "users.status"
        cached_data = {
            'dictionary_id': 'dict_1',
            'dictionary_name': '用户状态字典'
        }
        self.service._cache[cache_key] = cached_data
        
        result = self.service.get_field_semantic_mapping(
            self.mock_db, "users", "status"
        )
        
        assert result == cached_data
        # 确保没有调用数据库查询
        self.mock_db.query.assert_not_called()
    
    def test_get_semantic_value_with_mapping(self):
        """测试获取有映射的语义值"""
        semantic_info = {
            'dictionary_name': '用户状态字典',
            'value_mappings': {
                '1': {
                    'label': '激活',
                    'description': '用户已激活',
                    'is_active': True
                }
            }
        }
        
        result = self.service._get_semantic_value(1, semantic_info)
        
        assert result['original_value'] == 1
        assert result['semantic_label'] == '激活'
        assert result['description'] == '用户已激活'
        assert result['dictionary_name'] == '用户状态字典'
        assert result['is_active'] is True
    
    def test_get_semantic_value_without_mapping(self):
        """测试获取无映射的语义值"""
        semantic_info = {
            'dictionary_name': '用户状态字典',
            'value_mappings': {}
        }
        
        result = self.service._get_semantic_value(999, semantic_info)
        
        assert result['original_value'] == 999
        assert result['semantic_label'] is None
        assert "未找到值 '999' 的语义映射" in result['description']
        assert result['dictionary_name'] == '用户状态字典'
        assert result['is_active'] is True
    
    def test_get_semantic_value_null(self):
        """测试获取空值的语义值"""
        semantic_info = {
            'dictionary_name': '用户状态字典',
            'value_mappings': {}
        }
        
        result = self.service._get_semantic_value(None, semantic_info)
        
        assert result['original_value'] is None
        assert result['semantic_label'] is None
        assert result['description'] is None
        assert result['dictionary_name'] == '用户状态字典'
    
    def test_inject_semantic_values_empty_data(self):
        """测试注入语义值到空数据"""
        result = self.service.inject_semantic_values(self.mock_db, "users", [])
        assert result == []
    
    def test_inject_semantic_values_no_mappings(self):
        """测试注入语义值到无映射的表"""
        # Mock查询返回空列表
        self.mock_db.query.return_value.filter.return_value.all.return_value = []
        
        data = [{'id': 1, 'name': 'test'}]
        result = self.service.inject_semantic_values(self.mock_db, "users", data)
        
        assert result == data
    
    @patch.object(SemanticInjectionService, 'get_field_semantic_mapping')
    def test_inject_semantic_values_success(self, mock_get_mapping):
        """测试成功注入语义值"""
        # Mock字段映射
        mock_table = Mock(spec=DataTable)
        mock_table.table_name = "users"
        
        mock_field = Mock(spec=TableField)
        mock_field.field_name = "status"
        
        mock_field_mapping = Mock(spec=FieldMapping)
        mock_field_mapping.table = mock_table
        mock_field_mapping.field = mock_field
        
        # Mock查询链 - 模拟复杂的join查询
        query_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock = Mock()
        
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock
        filter_mock.all.return_value = [mock_field_mapping]
        
        self.mock_db.query.return_value = query_mock
        
        # Mock语义映射
        mock_get_mapping.return_value = {
            'dictionary_name': '用户状态字典',
            'value_mappings': {
                '1': {
                    'label': '激活',
                    'description': '用户已激活',
                    'is_active': True
                }
            }
        }
        
        data = [{'id': 1, 'status': 1, 'name': 'test'}]
        result = self.service.inject_semantic_values(self.mock_db, "users", data)
        
        assert len(result) == 1
        assert '_semantic' in result[0]
        assert 'status_semantic' in result[0]['_semantic']
        assert result[0]['_semantic']['status_semantic']['original_value'] == 1
        assert result[0]['_semantic']['status_semantic']['semantic_label'] == '激活'
    
    def test_get_table_semantic_schema_success(self):
        """测试成功获取表语义模式"""
        # Mock字段映射
        mock_table = Mock(spec=DataTable)
        mock_table.table_name = "users"
        
        mock_field = Mock(spec=TableField)
        mock_field.field_name = "status"
        
        mock_field_mapping = Mock(spec=FieldMapping)
        mock_field_mapping.table = mock_table
        mock_field_mapping.field = mock_field
        
        # Mock查询链 - 模拟复杂的join查询
        query_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock = Mock()
        
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock
        filter_mock.all.return_value = [mock_field_mapping]
        
        self.mock_db.query.return_value = query_mock
        
        # Mock语义映射
        with patch.object(self.service, 'get_field_semantic_mapping') as mock_get_mapping:
            mock_get_mapping.return_value = {
                'dictionary_name': '用户状态字典',
                'dictionary_code': 'USER_STATUS',
                'mapping_type': 'direct',
                'value_mappings': {'1': {'label': '激活'}, '0': {'label': '禁用'}}
            }
            
            result = self.service.get_table_semantic_schema(self.mock_db, "users")
            
            assert result['table_name'] == "users"
            assert 'status' in result['semantic_fields']
            assert result['semantic_fields']['status']['dictionary_name'] == '用户状态字典'
            assert result['semantic_fields']['status']['dictionary_code'] == 'USER_STATUS'
            assert result['semantic_fields']['status']['mapping_type'] == 'direct'
            assert result['semantic_fields']['status']['available_values'] == ['1', '0']
            assert result['metadata']['total_mapped_fields'] == 1
    
    def test_get_table_semantic_schema_no_mappings(self):
        """测试获取无映射的表语义模式"""
        # Mock查询链 - 模拟复杂的join查询返回空列表
        query_mock = Mock()
        join_mock1 = Mock()
        join_mock2 = Mock()
        filter_mock = Mock()
        
        query_mock.join.return_value = join_mock1
        join_mock1.join.return_value = join_mock2
        join_mock2.filter.return_value = filter_mock
        filter_mock.all.return_value = []
        
        self.mock_db.query.return_value = query_mock
        
        result = self.service.get_table_semantic_schema(self.mock_db, "users")
        
        assert result['table_name'] == "users"
        assert result['semantic_fields'] == {}
        assert result['metadata']['total_mapped_fields'] == 0
    
    def test_batch_inject_semantic_values_success(self):
        """测试批量注入语义值成功"""
        table_data_map = {
            'users': [{'id': 1, 'status': 1}],
            'orders': [{'id': 1, 'status': 'pending'}]
        }
        
        with patch.object(self.service, 'inject_semantic_values') as mock_inject:
            mock_inject.side_effect = [
                [{'id': 1, 'status': 1, '_semantic': {'status_semantic': {'original_value': 1, 'semantic_label': '激活'}}}],
                [{'id': 1, 'status': 'pending', '_semantic': {'status_semantic': {'original_value': 'pending', 'semantic_label': '待处理'}}}]
            ]
            
            result = self.service.batch_inject_semantic_values(self.mock_db, table_data_map)
            
            assert len(result) == 2
            assert 'users' in result
            assert 'orders' in result
            assert '_semantic' in result['users'][0]
            assert '_semantic' in result['orders'][0]
    
    def test_batch_inject_semantic_values_with_error(self):
        """测试批量注入语义值时部分失败"""
        table_data_map = {
            'users': [{'id': 1, 'status': 1}],
            'orders': [{'id': 1, 'status': 'pending'}]
        }
        
        with patch.object(self.service, 'inject_semantic_values') as mock_inject:
            # 第一个表成功，第二个表失败
            mock_inject.side_effect = [
                [{'id': 1, 'status': 1, '_semantic': {'status_semantic': {'original_value': 1, 'semantic_label': '激活'}}}],
                Exception("注入失败")
            ]
            
            result = self.service.batch_inject_semantic_values(self.mock_db, table_data_map)
            
            assert len(result) == 2
            assert 'users' in result
            assert 'orders' in result
            # 成功的表有语义信息
            assert '_semantic' in result['users'][0]
            # 失败的表返回原始数据
            assert result['orders'] == [{'id': 1, 'status': 'pending'}]
    
    def test_clear_cache(self):
        """测试清空缓存"""
        # 设置缓存
        self.service._cache['test'] = 'value'
        
        self.service.clear_cache()
        
        assert self.service._cache == {}
    
    def test_get_cache_stats(self):
        """测试获取缓存统计信息"""
        # 设置缓存
        self.service._cache['test1'] = 'value1'
        self.service._cache['test2'] = 'value2'
        
        stats = self.service.get_cache_stats()
        
        assert stats['cache_size'] == 2
        assert 'last_clear' in stats
        assert stats['ttl_minutes'] == 30
    
    def test_get_field_semantic_mapping_exception(self):
        """测试获取字段语义映射时发生异常"""
        # Mock数据库查询抛出异常
        self.mock_db.query.side_effect = Exception("数据库连接失败")
        
        result = self.service.get_field_semantic_mapping(
            self.mock_db, "users", "status"
        )
        
        assert result is None
    
    def test_inject_semantic_values_exception(self):
        """测试注入语义值时发生异常"""
        # Mock数据库查询抛出异常
        self.mock_db.query.side_effect = Exception("数据库连接失败")
        
        data = [{'id': 1, 'status': 1}]
        result = self.service.inject_semantic_values(self.mock_db, "users", data)
        
        # 异常时返回原始数据
        assert result == data
    
    def test_get_table_semantic_schema_exception(self):
        """测试获取表语义模式时发生异常"""
        # Mock数据库查询抛出异常
        self.mock_db.query.side_effect = Exception("数据库连接失败")
        
        result = self.service.get_table_semantic_schema(self.mock_db, "users")
        
        assert result['table_name'] == "users"
        assert result['semantic_fields'] == {}
        assert 'error' in result
        assert result['error'] == "数据库连接失败"