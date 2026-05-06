"""
数据源模块验收测试 - 聚焦版本

Task 1.5: 数据源模块验收
专注于核心功能验证，确保数据源模块独立可用
"""

import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.main import app
from src.utils.encryption import encrypt_password, decrypt_password


class TestDataSourceAcceptanceFocused:
    """数据源模块聚焦验收测试"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def valid_mysql_config(self):
        """有效的MySQL数据源配置"""
        return {
            "name": "验收测试MySQL数据源",
            "source_type": "DATABASE",
            "db_type": "MySQL",
            "host": "localhost",
            "port": 3306,
            "database_name": "test_db",
            "auth_type": "SQL_AUTH",
            "username": "test_user",
            "password": "test_password_123",
            "description": "用于验收测试的MySQL数据源",
            "status": True,
            "created_by": "acceptance_test"
        }

    def test_core_data_source_functionality(self, client, valid_mysql_config):
        """测试数据源核心功能：创建、查询、更新、删除"""
        
        # 1. 创建数据源
        create_response = client.post("/api/data-sources/", json=valid_mysql_config)
        assert create_response.status_code == 201, f"创建失败: {create_response.text}"
        
        created_source = create_response.json()
        source_id = created_source["id"]
        
        # 验证创建结果
        assert created_source["name"] == valid_mysql_config["name"]
        assert created_source["db_type"] == valid_mysql_config["db_type"]
        assert "password" not in created_source  # 密码已脱敏
        
        try:
            # 2. 查询单个数据源
            get_response = client.get(f"/api/data-sources/{source_id}")
            assert get_response.status_code == 200, f"查询失败: {get_response.text}"
            
            retrieved_source = get_response.json()
            assert retrieved_source["id"] == source_id
            assert retrieved_source["name"] == valid_mysql_config["name"]
            
            # 3. 更新数据源
            update_data = {"name": "更新后的验收测试数据源"}
            update_response = client.put(f"/api/data-sources/{source_id}", json=update_data)
            assert update_response.status_code == 200, f"更新失败: {update_response.text}"
            
            updated_source = update_response.json()
            assert updated_source["name"] == update_data["name"]
            
        finally:
            # 4. 删除数据源
            delete_response = client.delete(f"/api/data-sources/{source_id}")
            assert delete_response.status_code == 204, f"删除失败: {delete_response.text}"

    @patch('src.services.connection_test.ConnectionTestService.test_connection')
    def test_connection_testing(self, mock_test_connection, client, valid_mysql_config):
        """测试连接测试功能"""
        
        # Mock成功的连接测试
        mock_test_connection.return_value = MagicMock(
            success=True,
            message="连接成功",
            latency_ms=150
        )
        
        # 测试连接
        test_response = client.post("/api/data-sources/test", json=valid_mysql_config)
        assert test_response.status_code == 200, f"连接测试失败: {test_response.text}"
        
        test_result = test_response.json()
        assert test_result["success"] is True
        assert "latency_ms" in test_result

    def test_password_security(self):
        """测试密码加密安全性"""
        
        test_passwords = [
            "simple_password_123",
            "complex_P@ssw0rd!",
            "very_long_password_with_special_characters_!@#$%^&*()"
        ]
        
        for original_password in test_passwords:
            # 测试加密
            encrypted_password = encrypt_password(original_password)
            assert encrypted_password != original_password, "密码未被加密"
            
            # 测试解密
            decrypted_password = decrypt_password(encrypted_password)
            assert decrypted_password == original_password, "密码解密失败"

    def test_api_response_performance(self, client, valid_mysql_config):
        """测试API响应性能"""
        
        # 创建测试数据源
        create_response = client.post("/api/data-sources/", json=valid_mysql_config)
        assert create_response.status_code == 201
        source_id = create_response.json()["id"]
        
        try:
            # 测试查询响应时间
            response_times = []
            
            for _ in range(5):  # 执行5次查询
                start_time = time.time()
                response = client.get(f"/api/data-sources/{source_id}")
                end_time = time.time()
                
                assert response.status_code == 200
                response_times.append(end_time - start_time)
            
            # 验证平均响应时间小于200ms
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 0.2, f"平均响应时间过长: {avg_response_time:.4f}s"
            
        finally:
            # 清理测试数据
            client.delete(f"/api/data-sources/{source_id}")

    def test_data_validation_and_error_handling(self, client):
        """测试数据验证和错误处理"""
        
        # 测试无效数据
        invalid_configs = [
            {
                "name": "",  # 空名称
                "source_type": "DATABASE",
                "db_type": "MySQL",
                "created_by": "test"
            },
            {
                "name": "测试",
                "source_type": "DATABASE",
                "db_type": "SQL Server",
                # 缺少auth_type（SQL Server必需）
                "created_by": "test"
            }
        ]
        
        for invalid_config in invalid_configs:
            create_response = client.post("/api/data-sources/", json=invalid_config)
            assert create_response.status_code in [400, 422], "应该返回验证错误"
        
        # 测试不存在的资源
        get_response = client.get("/api/data-sources/non-existent-id")
        assert get_response.status_code == 404, "应该返回404错误"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])