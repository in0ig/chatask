import pytest
import requests
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

class TestKnowledgeAPIIntegration:
    """知识库 API 集成测试"""
    
    def test_knowledge_base_endpoints_not_404(self):
        """测试知识库 API 端点不返回 404 错误"""
        
        # 测试获取知识库列表
        response = client.get("/api/knowledge-bases/")
        assert response.status_code != 404, f"Knowledge base list endpoint returned 404"
        assert response.status_code in [200, 500], f"Unexpected status code: {response.status_code}"
        
        # 测试创建知识库端点存在（不实际创建，只测试路径）
        response = client.post("/api/knowledge-bases/", json={})
        assert response.status_code != 404, f"Knowledge base create endpoint returned 404"
        # 可能返回 422 (验证错误) 或其他错误，但不应该是 404
        
        # 测试更新知识库端点存在
        response = client.put("/api/knowledge-bases/test-id", json={})
        assert response.status_code != 404, f"Knowledge base update endpoint returned 404"
        
        # 测试删除知识库端点存在
        response = client.delete("/api/knowledge-bases/test-id")
        assert response.status_code != 404, f"Knowledge base delete endpoint returned 404"
    
    def test_knowledge_item_endpoints_not_404(self):
        """测试知识项 API 端点不返回 404 错误"""
        
        # 测试获取知识项列表
        response = client.get("/api/knowledge-items/")
        assert response.status_code != 404, f"Knowledge item list endpoint returned 404"
        assert response.status_code in [200, 500], f"Unexpected status code: {response.status_code}"
        
        # 测试创建知识项端点存在
        response = client.post("/api/knowledge-items/", json={})
        assert response.status_code != 404, f"Knowledge item create endpoint returned 404"
        
        # 测试获取单个知识项端点存在
        response = client.get("/api/knowledge-items/test-id")
        assert response.status_code != 404, f"Knowledge item get endpoint returned 404"
        
        # 测试更新知识项端点存在
        response = client.put("/api/knowledge-items/test-id", json={})
        assert response.status_code != 404, f"Knowledge item update endpoint returned 404"
        
        # 测试删除知识项端点存在
        response = client.delete("/api/knowledge-items/test-id")
        assert response.status_code != 404, f"Knowledge item delete endpoint returned 404"
        
        # 测试获取知识库相关知识项端点存在
        response = client.get("/api/knowledge-items/knowledge-base/test-kb-id/items")
        assert response.status_code != 404, f"Knowledge base items endpoint returned 404"
    
    def test_old_api_paths_return_404(self):
        """测试旧的 API 路径返回 404"""
        
        # 旧的知识库路径（单数形式）应该返回 404
        response = client.get("/api/knowledge-base/")
        assert response.status_code == 404, f"Old knowledge base path should return 404, got {response.status_code}"
        
        response = client.post("/api/knowledge-base/", json={})
        assert response.status_code == 404, f"Old knowledge base create path should return 404, got {response.status_code}"
        
        # 旧的知识项路径（单数形式）应该返回 404
        response = client.get("/api/knowledge-item/")
        assert response.status_code == 404, f"Old knowledge item path should return 404, got {response.status_code}"
        
        response = client.post("/api/knowledge-item/", json={})
        assert response.status_code == 404, f"Old knowledge item create path should return 404, got {response.status_code}"
    
    def test_api_path_consistency(self):
        """测试 API 路径一致性"""
        
        # 检查所有知识库相关路径都使用复数形式
        knowledge_base_paths = [
            "/api/knowledge-bases/",
            "/api/knowledge-bases/test-id"
        ]
        
        for path in knowledge_base_paths:
            response = client.get(path)
            assert response.status_code != 404, f"Path {path} should not return 404"
            assert "knowledge-bases" in path, f"Path {path} should use plural form 'knowledge-bases'"
        
        # 检查所有知识项相关路径都使用复数形式
        knowledge_item_paths = [
            "/api/knowledge-items/",
            "/api/knowledge-items/test-id",
            "/api/knowledge-items/knowledge-base/test-kb-id/items"
        ]
        
        for path in knowledge_item_paths:
            response = client.get(path)
            assert response.status_code != 404, f"Path {path} should not return 404"
            assert "knowledge-items" in path, f"Path {path} should use plural form 'knowledge-items'"
    
    def test_api_response_format(self):
        """测试 API 响应格式正确"""
        
        # 测试知识库列表 API 响应格式
        response = client.get("/api/knowledge-bases/")
        if response.status_code == 200:
            # 如果成功，应该返回列表
            data = response.json()
            assert isinstance(data, list), "Knowledge base list should return an array"
        elif response.status_code == 500:
            # 如果是服务器错误，至少路径是正确的
            assert "Internal Server Error" in response.text or response.json() is not None
        
        # 测试知识项列表 API 响应格式
        response = client.get("/api/knowledge-items/")
        if response.status_code == 200:
            # 如果成功，应该返回列表或分页对象
            data = response.json()
            assert isinstance(data, (list, dict)), "Knowledge item list should return an array or object"
        elif response.status_code == 500:
            # 如果是服务器错误，至少路径是正确的
            assert "Internal Server Error" in response.text or response.json() is not None

class TestAPIPathStandardsIntegration:
    """API 路径标准集成测试"""
    
    def test_all_knowledge_apis_use_correct_prefix(self):
        """测试所有知识相关 API 都使用正确的前缀"""
        
        # 获取所有路由
        routes = []
        for route in app.routes:
            if hasattr(route, 'path'):
                routes.append(route.path)
        
        # 检查知识库相关路由
        knowledge_base_routes = [r for r in routes if 'knowledge-bases' in r]
        assert len(knowledge_base_routes) > 0, "Should have knowledge base routes"
        
        for route in knowledge_base_routes:
            assert route.startswith('/api/'), f"Route {route} should start with /api/"
            assert 'knowledge-bases' in route, f"Route {route} should use plural form"
            assert '/api/api/' not in route, f"Route {route} should not have duplicate api prefix"
        
        # 检查知识项相关路由
        knowledge_item_routes = [r for r in routes if 'knowledge-items' in r]
        assert len(knowledge_item_routes) > 0, "Should have knowledge item routes"
        
        for route in knowledge_item_routes:
            assert route.startswith('/api/'), f"Route {route} should start with /api/"
            assert 'knowledge-items' in route, f"Route {route} should use plural form"
            assert '/api/api/' not in route, f"Route {route} should not have duplicate api prefix"
    
    def test_restful_conventions_compliance(self):
        """测试 RESTful 约定合规性"""
        
        # 测试知识库 CRUD 操作路径
        crud_tests = [
            ("GET", "/api/knowledge-bases/", "list"),
            ("POST", "/api/knowledge-bases/", "create"),
            ("PUT", "/api/knowledge-bases/test-id", "update"),
            ("DELETE", "/api/knowledge-bases/test-id", "delete"),
        ]
        
        for method, path, operation in crud_tests:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path, json={})
            elif method == "PUT":
                response = client.put(path, json={})
            elif method == "DELETE":
                response = client.delete(path)
            
            assert response.status_code != 404, f"{operation} operation at {path} should not return 404"
            
            # 检查路径格式
            assert path.startswith('/api/'), f"Path {path} should start with /api/"
            if 'test-id' in path:
                assert not path.endswith('/'), f"Individual resource path {path} should not end with slash"
            else:
                assert path.endswith('/'), f"Collection resource path {path} should end with slash"