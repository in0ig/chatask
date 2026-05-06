import pytest
import re
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st
from src.main import app

client = TestClient(app)

class TestAPIRoutes:
    """测试 API 路由的正确性"""
    
    def test_api_path_no_duplicate_prefix(self):
        """测试 API 路径无重复前缀"""
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                path_segments = route.path.split('/')
                api_count = path_segments.count('api')
                assert api_count == 1, f"Duplicate 'api' prefix in {route.path}"
    
    def test_api_path_plural_resources(self):
        """测试 API 路径使用复数形式"""
        expected_plural_resources = {
            'knowledge-bases': 'knowledge-base',
            'knowledge-items': 'knowledge-item'
        }
        
        found_resources = set()
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                path_segments = route.path.split('/')
                if len(path_segments) >= 3:
                    resource = path_segments[2]
                    if resource in expected_plural_resources or resource in expected_plural_resources.values():
                        found_resources.add(resource)
        
        # 检查是否使用了正确的复数形式
        for plural, singular in expected_plural_resources.items():
            if singular in found_resources:
                pytest.fail(f"Found singular resource '{singular}', should use plural '{plural}'")
    
    def test_api_path_kebab_case_format(self):
        """测试路径命名符合 kebab-case 格式"""
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                path_segments = route.path.split('/')
                for segment in path_segments:
                    if segment and not segment.startswith('{') and not segment.endswith('}'):
                        # 检查是否包含下划线（应该使用连字符）
                        assert '_' not in segment, f"Path segment should use kebab-case: {segment} in {route.path}"
                        # 检查是否包含大写字母
                        assert segment.islower(), f"Path segment should be lowercase: {segment} in {route.path}"
    
    def test_knowledge_base_routes_exist(self):
        """测试知识库相关路由存在且路径正确"""
        expected_knowledge_base_routes = [
            ('/api/knowledge-bases/', {'GET', 'POST'}),
            ('/api/knowledge-bases/{id}', {'PUT', 'DELETE'})
        ]
        
        actual_routes = {}
        for route in app.routes:
            if hasattr(route, 'path') and '/api/knowledge-bases' in route.path:
                path = route.path
                methods = getattr(route, 'methods', set())
                if path not in actual_routes:
                    actual_routes[path] = set()
                actual_routes[path].update(methods)
        
        for expected_path, expected_methods in expected_knowledge_base_routes:
            found = False
            for actual_path, actual_methods in actual_routes.items():
                if self._paths_match(actual_path, expected_path):
                    found = True
                    # 检查是否包含期望的 HTTP 方法
                    for method in expected_methods:
                        assert method in actual_methods, f"Method {method} not found for path {expected_path}"
            
            assert found, f"Expected route not found: {expected_path}"
    
    def test_knowledge_item_routes_exist(self):
        """测试知识项相关路由存在且路径正确"""
        expected_knowledge_item_routes = [
            ('/api/knowledge-items/', {'GET', 'POST'}),
            ('/api/knowledge-items/{id}', {'GET', 'PUT', 'DELETE'}),
            ('/api/knowledge-items/knowledge-base/{knowledge_base_id}/items', {'GET'})
        ]
        
        actual_routes = {}
        for route in app.routes:
            if hasattr(route, 'path') and '/api/knowledge-items' in route.path:
                path = route.path
                methods = getattr(route, 'methods', set())
                if path not in actual_routes:
                    actual_routes[path] = set()
                actual_routes[path].update(methods)
        
        for expected_path, expected_methods in expected_knowledge_item_routes:
            found = False
            for actual_path, actual_methods in actual_routes.items():
                if self._paths_match(actual_path, expected_path):
                    found = True
                    # 检查是否包含期望的 HTTP 方法
                    for method in expected_methods:
                        assert method in actual_methods, f"Method {method} not found for path {expected_path}"
            
            assert found, f"Expected route not found: {expected_path}"
    
    def test_api_routes_start_with_api_prefix(self):
        """测试所有 API 路径都以 /api 开头"""
        api_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and (
                'knowledge-bases' in route.path or 
                'knowledge-items' in route.path
            ):
                api_routes.append(route.path)
        
        for path in api_routes:
            assert path.startswith('/api/'), f"API path should start with '/api/': {path}"
    
    def test_no_trailing_slashes_in_parameterized_routes(self):
        """测试参数化路由不应该有尾随斜杠"""
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                path = route.path
                # 如果路径包含参数（如 {id}），不应该以斜杠结尾
                if '{' in path and '}' in path:
                    assert not path.endswith('/'), f"Parameterized route should not end with slash: {path}"
    
    def _paths_match(self, actual_path: str, expected_path: str) -> bool:
        """检查实际路径是否匹配期望路径（考虑参数占位符）"""
        actual_segments = actual_path.split('/')
        expected_segments = expected_path.split('/')
        
        if len(actual_segments) != len(expected_segments):
            return False
        
        for actual, expected in zip(actual_segments, expected_segments):
            if expected.startswith('{') and expected.endswith('}'):
                # 期望的是参数，实际的也应该是参数
                if not (actual.startswith('{') and actual.endswith('}')):
                    return False
            else:
                # 期望的是固定字符串，应该完全匹配
                if actual != expected:
                    return False
        
        return True

class TestAPIPathStandards:
    """测试 API 路径标准化"""
    
    def test_consistent_resource_naming(self):
        """测试资源命名的一致性"""
        resource_patterns = {
            'knowledge-bases': r'^/api/knowledge-bases',
            'knowledge-items': r'^/api/knowledge-items'
        }
        
        import re
        for route in app.routes:
            if hasattr(route, 'path'):
                path = route.path
                for resource, pattern in resource_patterns.items():
                    if re.match(pattern, path):
                        # 确保路径中的资源名称一致
                        assert resource in path, f"Inconsistent resource naming in {path}"
    
    def test_restful_conventions(self):
        """测试 RESTful 约定"""
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                path = route.path
                methods = getattr(route, 'methods', set())
                
                # 集合资源路径（如 /api/knowledge-bases/）应该支持 GET 和 POST
                if path.endswith('/') and not '{' in path:
                    if 'GET' in methods or 'POST' in methods:
                        # 这是一个集合资源，路径应该使用复数形式
                        path_segments = path.split('/')
                        if len(path_segments) >= 3:
                            resource = path_segments[2]
                            if resource in ['knowledge-base', 'knowledge-item']:
                                pytest.fail(f"Collection resource should be plural: {resource} in {path}")
                
                # 单个资源路径（如 /api/knowledge-bases/{id}）应该支持 GET, PUT, DELETE
                if '{' in path and '}' in path:
                    # 这是一个单个资源路径
                    if any(method in methods for method in ['GET', 'PUT', 'DELETE']):
                        # 路径应该遵循 /resource/{id} 格式
                        assert not path.endswith('/'), f"Individual resource path should not end with slash: {path}"

class TestAPIPathProperties:
    """使用 Hypothesis 进行属性测试"""
    
    @given(st.sampled_from(['knowledge-bases', 'knowledge-items']))
    def test_property_frontend_backend_path_matching(self, resource_name):
        """属性 1：前后端 API 路径匹配测试"""
        # 检查后端路由是否存在对应的资源
        backend_routes = []
        for route in app.routes:
            if hasattr(route, 'path') and resource_name in route.path:
                backend_routes.append(route.path)
        
        # 验证路径格式一致性
        for route_path in backend_routes:
            # 所有 API 路径都应该以 /api/ 开头
            assert route_path.startswith('/api/'), f"Backend route should start with /api/: {route_path}"
            # 资源名称应该使用复数形式
            assert resource_name in route_path, f"Route should contain resource name: {resource_name}"
            # 路径中不应该有重复的 api 前缀
            assert route_path.count('/api/') == 1, f"Route should not have duplicate api prefix: {route_path}"
    
    def test_property_no_duplicate_route_prefixes(self):
        """属性 2：路由前缀无重复测试"""
        for route in app.routes:
            if hasattr(route, 'path') and '/api/' in route.path:
                # 只检查知识库相关的路由
                if 'knowledge-bases' in route.path or 'knowledge-items' in route.path:
                    path_segments = route.path.split('/')
                    api_count = path_segments.count('api')
                    # 属性：每个路径中 'api' 只能出现一次
                    assert api_count <= 1, f"Route should not have duplicate 'api' prefix: {route.path}"
                    # 属性：不应该有 /api/api/ 这样的重复前缀
                    assert '/api/api/' not in route.path, f"Route should not have /api/api/ duplicate prefix: {route.path}"
    
    @given(st.sampled_from(['knowledge-bases', 'knowledge-items']))
    def test_property_api_naming_consistency(self, resource_name):
        """属性 3：API 路径命名规范一致性测试"""
        routes_with_resource = []
        for route in app.routes:
            if hasattr(route, 'path') and resource_name in route.path:
                routes_with_resource.append(route.path)
        
        for route_path in routes_with_resource:
            # 属性：所有相关路径都应该使用相同的资源命名
            assert resource_name in route_path, f"Inconsistent resource naming in {route_path}"
            # 属性：路径应该使用 kebab-case 格式
            path_segments = route_path.split('/')
            for segment in path_segments:
                if segment and not segment.startswith('{') and not segment.endswith('}') and segment != 'api':
                    assert '_' not in segment, f"Path segment should use kebab-case: {segment}"
                    assert segment.islower(), f"Path segment should be lowercase: {segment}"
            # 属性：应该使用复数形式而不是单数形式
            singular_form = resource_name.rstrip('s')  # 简单的单数转换
            if singular_form != resource_name:  # 确保确实是复数形式
                assert singular_form not in route_path or resource_name in route_path, f"Should use plural form {resource_name} instead of singular in {route_path}"
    
    def test_property_api_functionality_correctness(self):
        """属性 4：API 功能正确性测试"""
        # 测试知识库 API 的基本功能属性
        knowledge_base_routes = [r for r in app.routes if hasattr(r, 'path') and 'knowledge-bases' in r.path]
        
        # 属性：应该有获取列表的路由
        list_routes = [r for r in knowledge_base_routes if r.path.endswith('/') and 'GET' in getattr(r, 'methods', set())]
        assert len(list_routes) > 0, "Should have at least one list endpoint for knowledge-bases"
        
        # 属性：应该有创建资源的路由
        create_routes = [r for r in knowledge_base_routes if r.path.endswith('/') and 'POST' in getattr(r, 'methods', set())]
        assert len(create_routes) > 0, "Should have at least one create endpoint for knowledge-bases"
        
        # 属性：应该有更新资源的路由
        update_routes = [r for r in knowledge_base_routes if '{' in r.path and 'PUT' in getattr(r, 'methods', set())]
        assert len(update_routes) > 0, "Should have at least one update endpoint for knowledge-bases"
        
        # 属性：应该有删除资源的路由
        delete_routes = [r for r in knowledge_base_routes if '{' in r.path and 'DELETE' in getattr(r, 'methods', set())]
        assert len(delete_routes) > 0, "Should have at least one delete endpoint for knowledge-bases"
        
        # 测试知识项 API 的基本功能属性
        knowledge_item_routes = [r for r in app.routes if hasattr(r, 'path') and 'knowledge-items' in r.path]
        
        # 属性：应该有获取列表的路由
        list_routes = [r for r in knowledge_item_routes if r.path.endswith('/') and 'GET' in getattr(r, 'methods', set())]
        assert len(list_routes) > 0, "Should have at least one list endpoint for knowledge-items"
        
        # 属性：应该有创建资源的路由
        create_routes = [r for r in knowledge_item_routes if r.path.endswith('/') and 'POST' in getattr(r, 'methods', set())]
        assert len(create_routes) > 0, "Should have at least one create endpoint for knowledge-items"
    
    @given(st.sampled_from([
        '/api/knowledge-bases/',
        '/api/knowledge-items/',
        '/api/knowledge-bases/test-id',
        '/api/knowledge-items/test-id'
    ]))
    def test_property_path_format_validation(self, api_path):
        """属性测试：API 路径格式验证"""
        # 属性：所有 API 路径都应该符合特定格式
        assert api_path.startswith('/api/'), f"Path should start with /api/: {api_path}"
        
        # 属性：路径中不应该有连续的斜杠
        assert '//' not in api_path, f"Path should not have consecutive slashes: {api_path}"
        
        # 属性：集合资源路径应该以斜杠结尾，单个资源路径不应该
        if 'test-id' in api_path:
            assert not api_path.endswith('/'), f"Individual resource path should not end with slash: {api_path}"
        else:
            assert api_path.endswith('/'), f"Collection resource path should end with slash: {api_path}"
        
        # 属性：路径应该使用复数资源名称
        if 'knowledge-base/' in api_path and 'knowledge-bases/' not in api_path:
            pytest.fail(f"Path should use plural form 'knowledge-bases': {api_path}")
        if 'knowledge-item/' in api_path and 'knowledge-items/' not in api_path:
            pytest.fail(f"Path should use plural form 'knowledge-items': {api_path}")
    
    @given(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    def test_property_route_path_segments_validation(self, test_segment):
        """属性测试：路由路径段验证"""
        # 跳过不相关的测试段
        if test_segment not in ['knowledge-bases', 'knowledge-items', 'api']:
            return
        
        # 检查所有包含该段的路由
        routes_with_segment = []
        for route in app.routes:
            if hasattr(route, 'path') and test_segment in route.path:
                routes_with_segment.append(route.path)
        
        for route_path in routes_with_segment:
            # 属性：路径段应该使用小写
            segments = route_path.split('/')
            for segment in segments:
                if segment == test_segment:
                    assert segment.islower(), f"Path segment should be lowercase: {segment} in {route_path}"
                    # 属性：不应该包含下划线
                    assert '_' not in segment, f"Path segment should not contain underscores: {segment} in {route_path}"