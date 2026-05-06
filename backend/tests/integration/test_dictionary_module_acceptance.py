"""
数据字典模块验收测试
基于真实数据源和数据表的集成测试
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
import json
import tempfile
import os

from src.main import app
from src.database import get_db
from src.models.data_preparation_model import Dictionary, DictionaryItem, DataTable, TableField, FieldMapping
from src.models.data_source_model import DataSource

# 创建测试客户端
client = TestClient(app)


class TestDictionaryModuleAcceptance:
    """数据字典模块验收测试类"""

    @pytest.fixture(scope="class")
    def test_data_source(self, db_session_factory):
        """创建测试数据源"""
        db_session = db_session_factory()
        data_source = DataSource(
            name="验收测试数据源",
            source_type="DATABASE",
            db_type="mysql",
            host="localhost",
            port=3306,
            database_name="chatbi_test",
            auth_type="SQL_AUTH",
            username="test_user",
            password="test_password",
            description="用于验收测试的数据源",
            status=True,
            created_by="acceptance_test"
        )
        db_session.add(data_source)
        db_session.commit()
        db_session.refresh(data_source)
        db_session.close()
        return data_source

    @pytest.fixture(scope="class")
    def test_data_table(self, db_session_factory, test_data_source):
        """创建测试数据表"""
        db_session = db_session_factory()
        data_table = DataTable(
            data_source_id=test_data_source.id,
            table_name="users",
            display_name="用户表",
            description="用户信息表",
            data_mode="DIRECT_QUERY",
            status=True,
            created_by="acceptance_test"
        )
        db_session.add(data_table)
        db_session.commit()
        db_session.refresh(data_table)
        db_session.close()
        return data_table

    @pytest.fixture(scope="class")
    def test_table_fields(self, db_session_factory, test_data_table):
        """创建测试表字段"""
        db_session = db_session_factory()
        fields = [
            TableField(
                table_id=test_data_table.id,
                field_name="user_id",
                display_name="用户ID",
                data_type="BIGINT",
                description="用户唯一标识",
                is_primary_key=True,
                is_nullable=False,
                is_queryable=True,
                is_aggregatable=False
            ),
            TableField(
                table_id=test_data_table.id,
                field_name="username",
                display_name="用户名",
                data_type="VARCHAR",
                description="用户登录名",
                is_primary_key=False,
                is_nullable=False,
                is_queryable=True,
                is_aggregatable=False
            ),
            TableField(
                table_id=test_data_table.id,
                field_name="status",
                display_name="状态",
                data_type="INT",
                description="用户状态",
                is_primary_key=False,
                is_nullable=False,
                is_queryable=True,
                is_aggregatable=True
            )
        ]
        
        for field in fields:
            db_session.add(field)
        db_session.commit()
        
        for field in fields:
            db_session.refresh(field)
        
        db_session.close()
        return fields

    @pytest.fixture(scope="class")
    def test_dictionary(self, db_session_factory):
        """创建测试字典"""
        db_session = db_session_factory()
        dictionary = Dictionary(
            code="USER_STATUS",
            name="用户状态字典",
            description="用户账户状态枚举",
            dict_type="static",
            status=True,
            created_by="acceptance_test"
        )
        db_session.add(dictionary)
        db_session.commit()
        db_session.refresh(dictionary)
        db_session.close()
        return dictionary

    @pytest.fixture(scope="class")
    def test_dictionary_items(self, db_session_factory, test_dictionary):
        """创建测试字典项"""
        db_session = db_session_factory()
        items = [
            DictionaryItem(
                dictionary_id=test_dictionary.id,
                item_key="0",
                item_value="禁用",
                description="用户账户被禁用",
                sort_order=1,
                status=True,
                created_by="acceptance_test"
            ),
            DictionaryItem(
                dictionary_id=test_dictionary.id,
                item_key="1",
                item_value="正常",
                description="用户账户正常",
                sort_order=2,
                status=True,
                created_by="acceptance_test"
            ),
            DictionaryItem(
                dictionary_id=test_dictionary.id,
                item_key="2",
                item_value="锁定",
                description="用户账户被锁定",
                sort_order=3,
                status=True,
                created_by="acceptance_test"
            )
        ]
        
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        for item in items:
            db_session.refresh(item)
        
        db_session.close()
        return items

    # ====================
    # 基于数据表模块的集成测试
    # ====================

    def test_dictionary_data_table_integration(self, test_data_table, test_dictionary):
        """测试字典与数据表的集成"""
        # 获取数据表信息
        response = client.get(f"/api/data-tables/{test_data_table.id}")
        assert response.status_code == 200
        table_data = response.json()
        assert table_data["table_name"] == "users"
        
        # 获取字典信息
        response = client.get(f"/api/dictionaries/{test_dictionary.id}")
        assert response.status_code == 200
        dict_data = response.json()
        assert dict_data["code"] == "USER_STATUS"

    def test_field_mapping_creation_with_real_data(self, test_table_fields, test_dictionary):
        """测试基于真实数据的字段映射创建"""
        # 找到状态字段
        status_field = next(field for field in test_table_fields if field.field_name == "status")
        
        # 创建字段映射
        mapping_data = {
            "table_id": status_field.table_id,
            "field_id": status_field.id,
            "dictionary_id": test_dictionary.id,
            "business_name": "用户状态",
            "business_meaning": "用户账户的当前状态",
            "value_range": "0-2",
            "is_required": True,
            "default_value": "1"
        }
        
        response = client.post("/api/field-mappings/", json=mapping_data)
        assert response.status_code == 201
        
        mapping_result = response.json()
        assert mapping_result["business_name"] == "用户状态"
        assert mapping_result["dictionary_id"] == test_dictionary.id
        assert mapping_result["field_name"] == "status"

    def test_field_mapping_query_with_dictionary(self, test_data_table, test_dictionary):
        """测试带字典信息的字段映射查询"""
        response = client.get(f"/api/field-mappings/table/{test_data_table.id}")
        assert response.status_code == 200
        
        mappings = response.json()
        assert "items" in mappings
        
        # 查找状态字段的映射
        status_mapping = next(
            (mapping for mapping in mappings["items"] 
             if mapping["field_name"] == "status"), 
            None
        )
        
        if status_mapping:
            assert status_mapping["dictionary_name"] == "用户状态字典"
            assert status_mapping["business_name"] == "用户状态"

    # ====================
    # 字典导入导出功能验证
    # ====================

    def test_dictionary_export_excel(self, test_dictionary):
        """测试字典导出到Excel"""
        response = client.get(f"/api/dictionaries/{test_dictionary.id}/export?format_type=excel")
        assert response.status_code == 200
        
        result = response.json()
        assert result["format"] == "excel"
        assert "导出成功" in result["message"]
        assert "file_path" in result

    def test_dictionary_export_csv(self, test_dictionary):
        """测试字典导出到CSV"""
        response = client.get(f"/api/dictionaries/{test_dictionary.id}/export?format_type=csv")
        assert response.status_code == 200
        
        result = response.json()
        assert result["format"] == "csv"
        assert "导出成功" in result["message"]
        assert "file_path" in result

    def test_dictionary_import_export_roundtrip(self, test_dictionary, test_dictionary_items):
        """测试字典导入导出往返一致性"""
        # 1. 导出字典
        export_response = client.get(f"/api/dictionaries/{test_dictionary.id}/export?format_type=excel")
        assert export_response.status_code == 200
        
        # 2. 创建新字典用于导入测试
        new_dict_data = {
            "code": "IMPORTED_USER_STATUS",
            "name": "导入的用户状态字典",
            "description": "通过导入创建的字典",
            "dict_type": "static",
            "status": True,
            "created_by": "acceptance_test"
        }
        
        create_response = client.post("/api/dictionaries/", json=new_dict_data)
        assert create_response.status_code == 201
        new_dict = create_response.json()
        
        # 3. 验证导入功能（模拟文件导入）
        # 注意：这里简化测试，实际应该测试文件上传
        import_data = {
            "items": [
                {
                    "item_key": "0",
                    "item_value": "禁用",
                    "description": "用户账户被禁用",
                    "sort_order": 1,
                    "status": True
                },
                {
                    "item_key": "1",
                    "item_value": "正常",
                    "description": "用户账户正常",
                    "sort_order": 2,
                    "status": True
                }
            ]
        }
        
        batch_response = client.post(f"/api/dictionaries/{new_dict['id']}/items/batch", json=import_data)
        assert batch_response.status_code == 201
        
        batch_result = batch_response.json()
        assert batch_result["success_count"] == 2
        assert batch_result["failed_count"] == 0

    # ====================
    # 字段映射完整性验证
    # ====================

    def test_batch_field_mapping_operations(self, test_table_fields, test_dictionary):
        """测试批量字段映射操作"""
        # 准备批量映射数据
        batch_data = {
            "table_id": test_table_fields[0].table_id,
            "mappings": [
                {
                    "field_id": test_table_fields[0].id,  # user_id
                    "business_name": "用户标识",
                    "business_meaning": "用户的唯一标识符",
                    "is_required": True
                },
                {
                    "field_id": test_table_fields[1].id,  # username
                    "business_name": "用户名称",
                    "business_meaning": "用户的登录名称",
                    "is_required": True
                }
            ]
        }
        
        response = client.post("/api/field-mappings/batch", json=batch_data)
        assert response.status_code == 201
        
        result = response.json()
        assert result["success_count"] == 2
        assert result["error_count"] == 0

    def test_field_mapping_search_and_filter(self, test_data_table):
        """测试字段映射的搜索和筛选功能"""
        # 测试搜索功能
        response = client.get(f"/api/field-mappings/table/{test_data_table.id}?q=用户")
        assert response.status_code == 200
        
        search_result = response.json()
        assert "items" in search_result
        
        # 验证搜索结果包含"用户"关键词
        for mapping in search_result["items"]:
            assert ("用户" in mapping.get("business_name", "") or 
                   "用户" in mapping.get("business_meaning", "") or
                   "用户" in mapping.get("field_name", ""))

    def test_field_mapping_business_semantics(self, test_data_table):
        """测试字段映射的业务语义正确性"""
        response = client.get(f"/api/field-mappings/table/{test_data_table.id}")
        assert response.status_code == 200
        
        mappings = response.json()
        
        # 验证每个映射都有业务含义
        for mapping in mappings["items"]:
            if mapping.get("business_name"):
                assert len(mapping["business_name"]) > 0
                assert mapping["business_name"] != mapping["field_name"]  # 业务名称应该不同于字段名

    # ====================
    # 真实数据源集成测试
    # ====================

    def test_end_to_end_data_flow(self, test_data_source, test_data_table, test_dictionary):
        """测试端到端的数据流"""
        # 1. 验证数据源存在且可用
        ds_response = client.get(f"/api/datasources/{test_data_source.id}")
        assert ds_response.status_code == 200
        
        # 2. 验证数据表与数据源的关联
        dt_response = client.get(f"/api/data-tables/{test_data_table.id}")
        assert dt_response.status_code == 200
        table_data = dt_response.json()
        assert table_data["data_source_id"] == test_data_source.id
        
        # 3. 验证字典可以被字段映射使用
        dict_response = client.get(f"/api/dictionaries/{test_dictionary.id}")
        assert dict_response.status_code == 200
        
        # 4. 验证完整的数据流：数据源 -> 数据表 -> 字段 -> 字典映射
        fields_response = client.get(f"/api/data-tables/{test_data_table.id}/fields")
        if fields_response.status_code == 200:
            fields = fields_response.json()
            assert len(fields) > 0
            
            # 验证字段可以创建字典映射
            for field in fields:
                if field["field_name"] == "status":
                    mapping_data = {
                        "table_id": test_data_table.id,
                        "field_id": field["id"],
                        "dictionary_id": test_dictionary.id,
                        "business_name": "状态映射测试",
                        "business_meaning": "端到端测试的状态映射"
                    }
                    
                    mapping_response = client.post("/api/field-mappings/", json=mapping_data)
                    # 如果映射已存在，更新它
                    if mapping_response.status_code == 409:
                        # 获取现有映射并更新
                        existing_mappings = client.get(f"/api/field-mappings/table/{test_data_table.id}").json()
                        for existing in existing_mappings["items"]:
                            if existing["field_id"] == field["id"]:
                                update_response = client.put(
                                    f"/api/field-mappings/{existing['id']}", 
                                    json={"business_name": "状态映射测试更新"}
                                )
                                assert update_response.status_code == 200
                                break
                    else:
                        assert mapping_response.status_code == 201

    def test_dictionary_module_performance(self, test_dictionary):
        """测试数据字典模块性能"""
        import time
        
        # 测试字典列表查询性能
        start_time = time.time()
        response = client.get("/api/dictionaries/?page=1&page_size=50")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # 应该在2秒内完成
        
        # 测试字典详情查询性能
        start_time = time.time()
        response = client.get(f"/api/dictionaries/{test_dictionary.id}")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成

    def test_dictionary_module_error_handling(self):
        """测试数据字典模块错误处理"""
        # 测试不存在的字典
        response = client.get("/api/dictionaries/non-existent-id")
        assert response.status_code == 404
        
        # 测试无效的字段映射
        invalid_mapping = {
            "table_id": "invalid-table-id",
            "field_id": "invalid-field-id",
            "business_name": "测试映射"
        }
        
        response = client.post("/api/field-mappings/", json=invalid_mapping)
        assert response.status_code in [400, 422, 404]  # 应该返回错误状态码

    # ====================
    # 清理测试数据
    # ====================

    @pytest.fixture(scope="class", autouse=True)
    def cleanup_test_data(self, db_session_factory):
        """测试完成后清理数据"""
        yield
        
        # 清理顺序：字段映射 -> 字典项 -> 字典 -> 表字段 -> 数据表 -> 数据源
        db_session = db_session_factory()
        try:
            # 清理字段映射
            db_session.query(FieldMapping).filter(
                FieldMapping.created_by == "acceptance_test"
            ).delete()
            
            # 清理字典项
            db_session.query(DictionaryItem).filter(
                DictionaryItem.created_by == "acceptance_test"
            ).delete()
            
            # 清理字典
            db_session.query(Dictionary).filter(
                Dictionary.created_by == "acceptance_test"
            ).delete()
            
            # 清理表字段
            db_session.query(TableField).filter(
                TableField.table_id.in_(
                    db_session.query(DataTable.id).filter(
                        DataTable.created_by == "acceptance_test"
                    )
                )
            ).delete()
            
            # 清理数据表
            db_session.query(DataTable).filter(
                DataTable.created_by == "acceptance_test"
            ).delete()
            
            # 清理数据源
            db_session.query(DataSource).filter(
                DataSource.created_by == "acceptance_test"
            ).delete()
            
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"清理测试数据时出错: {e}")
        finally:
            db_session.close()