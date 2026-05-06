"""
语义相似度计算引擎 API 单元测试

任务 5.2.2 的 API 测试实现
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.main import app
from src.services.semantic_similarity_engine import KeywordAnalysis, SemanticMatch


class TestSemanticSimilarityAPI:
    """语义相似度计算引擎 API 测试"""
    
    def setup_method(self):
        """测试前置设置"""
        self.client = TestClient(app)
    
    def test_analyze_question_success(self):
        """测试问题分析成功"""
        request_data = {
            "user_question": "查询用户订单的销售金额统计"
        }
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "chinese_terms" in data["data"]
        assert "english_terms" in data["data"]
        assert "business_keywords" in data["data"]
        assert "all_keywords" in data["data"]
        assert len(data["data"]["all_keywords"]) > 0
    
    def test_analyze_question_empty_input(self):
        """测试空输入"""
        request_data = {
            "user_question": ""
        }
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 400
        assert "用户问题不能为空" in response.json()["detail"]
    
    def test_analyze_question_missing_field(self):
        """测试缺少字段"""
        request_data = {}
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 400
    
    def test_calculate_table_similarity_success(self):
        """测试表相似度计算成功"""
        request_data = {
            "user_question": "查询用户订单数据",
            "tables": [
                {
                    "id": "table_1",
                    "table_name": "user_order",
                    "table_comment": "用户订单表",
                    "fields": []
                },
                {
                    "id": "table_2",
                    "table_name": "product_info",
                    "table_comment": "产品信息表",
                    "fields": []
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-table-similarity", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "keyword_analysis" in data["data"]
        assert "table_matches" in data["data"]
        assert len(data["data"]["table_matches"]) > 0
        
        # 验证匹配结果结构
        match = data["data"]["table_matches"][0]
        assert "table_id" in match
        assert "table_name" in match
        assert "similarity_score" in match
        assert "match_reasons" in match
        assert "matched_keywords" in match
    
    def test_calculate_table_similarity_empty_tables(self):
        """测试空表列表"""
        request_data = {
            "user_question": "查询用户数据",
            "tables": []
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-table-similarity", json=request_data)
        
        assert response.status_code == 400
        assert "表信息不能为空" in response.json()["detail"]
    
    def test_calculate_field_similarity_success(self):
        """测试字段相似度计算成功"""
        request_data = {
            "user_question": "查询用户姓名和年龄",
            "fields": [
                {
                    "id": "field_1",
                    "field_name": "user_name",
                    "field_type": "varchar(100)",
                    "field_comment": "用户姓名"
                },
                {
                    "id": "field_2",
                    "field_name": "user_age",
                    "field_type": "int",
                    "field_comment": "用户年龄"
                }
            ],
            "table_context": {
                "table_name": "user_info",
                "table_comment": "用户信息表"
            }
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-field-similarity", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "field_matches" in data["data"]
        assert len(data["data"]["field_matches"]) > 0
        
        # 验证匹配结果结构
        match = data["data"]["field_matches"][0]
        assert "field_id" in match
        assert "field_name" in match
        assert "similarity_score" in match
        assert "technical_mapping" in match
    
    def test_calculate_field_similarity_empty_fields(self):
        """测试空字段列表"""
        request_data = {
            "user_question": "查询数据",
            "fields": []
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-field-similarity", json=request_data)
        
        assert response.status_code == 400
        assert "字段信息不能为空" in response.json()["detail"]
    
    def test_business_term_mapping_success(self):
        """测试业务术语映射成功"""
        request_data = {
            "user_question": "查询客户信息",
            "business_terms": [
                {
                    "id": "term_1",
                    "name": "客户",
                    "description": "购买产品或服务的个人或组织",
                    "aliases": ["用户", "顾客"]
                },
                {
                    "id": "term_2",
                    "name": "订单",
                    "description": "客户的购买请求",
                    "aliases": ["购买单", "采购单"]
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/business-term-mapping", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "business_term_matches" in data["data"]
        assert len(data["data"]["business_term_matches"]) > 0
    
    def test_business_term_mapping_empty_terms(self):
        """测试空业务术语列表"""
        request_data = {
            "user_question": "查询数据",
            "business_terms": []
        }
        
        response = self.client.post("/api/semantic-similarity/business-term-mapping", json=request_data)
        
        assert response.status_code == 400
        assert "业务术语不能为空" in response.json()["detail"]
    
    def test_knowledge_term_matching_success(self):
        """测试知识库术语匹配成功"""
        request_data = {
            "user_question": "查询销售业绩数据",
            "knowledge_items": [
                {
                    "id": "knowledge_1",
                    "name": "销售业绩",
                    "description": "销售人员在特定时期内的销售成果",
                    "type": "TERM",
                    "keywords": ["销售", "业绩", "成果"]
                },
                {
                    "id": "knowledge_2",
                    "name": "客户满意度",
                    "description": "客户对产品或服务的满意程度",
                    "type": "LOGIC",
                    "keywords": ["客户", "满意度", "评价"]
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/knowledge-term-matching", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "knowledge_matches" in data["data"]
        assert len(data["data"]["knowledge_matches"]) > 0
    
    def test_knowledge_term_matching_empty_items(self):
        """测试空知识库项目列表"""
        request_data = {
            "user_question": "查询数据",
            "knowledge_items": []
        }
        
        response = self.client.post("/api/semantic-similarity/knowledge-term-matching", json=request_data)
        
        assert response.status_code == 400
        assert "知识库项目不能为空" in response.json()["detail"]
    
    def test_comprehensive_similarity_success(self):
        """测试综合相似度计算成功"""
        request_data = {
            "user_question": "查询用户订单销售数据",
            "tables": [
                {
                    "id": "table_1",
                    "table_name": "user_order",
                    "table_comment": "用户订单表",
                    "fields": []
                }
            ],
            "business_terms": [
                {
                    "id": "term_1",
                    "name": "用户",
                    "description": "系统使用者",
                    "aliases": ["客户"]
                }
            ],
            "knowledge_items": [
                {
                    "id": "knowledge_1",
                    "name": "销售数据",
                    "description": "销售相关的数据信息",
                    "type": "TERM",
                    "keywords": ["销售", "数据"]
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/comprehensive-similarity", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "keyword_analysis" in data["data"]
        assert "table_matches" in data["data"]
        assert "business_term_matches" in data["data"]
        assert "knowledge_matches" in data["data"]
    
    def test_comprehensive_similarity_empty_question(self):
        """测试综合相似度计算空问题"""
        request_data = {
            "user_question": "",
            "tables": [],
            "business_terms": [],
            "knowledge_items": []
        }
        
        response = self.client.post("/api/semantic-similarity/comprehensive-similarity", json=request_data)
        
        assert response.status_code == 400
        assert "用户问题不能为空" in response.json()["detail"]
    
    def test_comprehensive_similarity_partial_data(self):
        """测试综合相似度计算部分数据"""
        request_data = {
            "user_question": "查询用户数据",
            "tables": [
                {
                    "id": "table_1",
                    "table_name": "user_info",
                    "table_comment": "用户信息表",
                    "fields": []
                }
            ]
            # 只提供表数据，不提供业务术语和知识库项目
        }
        
        response = self.client.post("/api/semantic-similarity/comprehensive-similarity", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "table_matches" in data["data"]
        # 应该只有表匹配结果，没有业务术语和知识库匹配
        assert "business_term_matches" not in data["data"]
        assert "knowledge_matches" not in data["data"]
    
    def test_get_statistics_success(self):
        """测试获取统计信息成功"""
        response = self.client.get("/api/semantic-similarity/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "business_term_mappings_count" in data["data"]
        assert "technical_term_mappings_count" in data["data"]
        assert "weights" in data["data"]
    
    def test_health_check_success(self):
        """测试健康检查成功"""
        response = self.client.get("/api/semantic-similarity/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["service"] == "semantic_similarity_engine"
        assert data["data"]["status"] == "healthy"
    
    def test_invalid_json_format(self):
        """测试无效JSON格式"""
        response = self.client.post(
            "/api/semantic-similarity/analyze-question",
            data="invalid json"
        )
        
        assert response.status_code == 422
    
    def test_large_input_handling(self):
        """测试大输入处理"""
        # 创建大量表数据
        large_tables = []
        for i in range(100):
            large_tables.append({
                "id": f"table_{i}",
                "table_name": f"test_table_{i}",
                "table_comment": f"测试表{i}",
                "fields": []
            })
        
        request_data = {
            "user_question": "查询测试数据",
            "tables": large_tables
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-table-similarity", json=request_data)
        
        # 应该能正常处理大量数据
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["table_matches"]) <= 10  # 应该有排序和限制
    
    def test_special_characters_in_question(self):
        """测试问题中的特殊字符"""
        request_data = {
            "user_question": "查询用户@#$%订单！！！数据？？？"
        }
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 应该能正确处理特殊字符
        assert len(data["data"]["all_keywords"]) > 0
    
    def test_mixed_language_question(self):
        """测试中英文混合问题"""
        request_data = {
            "user_question": "查询user表中的order数据统计"
        }
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["chinese_terms"]) > 0
        assert len(data["data"]["english_terms"]) > 0
    
    @patch('src.services.semantic_similarity_engine.SemanticSimilarityEngine.analyze_user_question')
    def test_service_error_handling(self, mock_analyze):
        """测试服务错误处理"""
        # 模拟服务抛出异常
        mock_analyze.side_effect = Exception("Service error")
        
        request_data = {
            "user_question": "测试问题"
        }
        
        response = self.client.post("/api/semantic-similarity/analyze-question", json=request_data)
        
        assert response.status_code == 500
        assert "分析用户问题失败" in response.json()["detail"]
    
    def test_field_similarity_with_context(self):
        """测试带上下文的字段相似度计算"""
        request_data = {
            "user_question": "查询用户姓名",
            "fields": [
                {
                    "field_name": "name",
                    "field_type": "varchar(50)",
                    "field_comment": "姓名"
                }
            ],
            "table_context": {
                "table_name": "user_info",
                "table_comment": "用户信息表"
            }
        }
        
        response = self.client.post("/api/semantic-similarity/calculate-field-similarity", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 有上下文的字段匹配应该有更高的相似度
        assert len(data["data"]["field_matches"]) > 0
    
    def test_business_term_with_aliases(self):
        """测试带别名的业务术语匹配"""
        request_data = {
            "user_question": "查询顾客信息",
            "business_terms": [
                {
                    "id": "term_1",
                    "name": "客户",
                    "description": "购买产品的人",
                    "aliases": ["顾客", "用户", "买家"]
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/business-term-mapping", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 应该通过别名匹配到客户术语
        matches = data["data"]["business_term_matches"]
        assert len(matches) > 0
        assert matches[0]["similarity_score"] > 0.5
    
    def test_knowledge_item_type_weighting(self):
        """测试知识库项目类型权重"""
        request_data = {
            "user_question": "查询销售规则",
            "knowledge_items": [
                {
                    "id": "knowledge_1",
                    "name": "销售规则",
                    "description": "销售相关的业务规则",
                    "type": "TERM",
                    "keywords": ["销售", "规则"]
                },
                {
                    "id": "knowledge_2",
                    "name": "销售流程",
                    "description": "销售的业务流程",
                    "type": "LOGIC",
                    "keywords": ["销售", "流程"]
                }
            ]
        }
        
        response = self.client.post("/api/semantic-similarity/knowledge-term-matching", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        matches = data["data"]["knowledge_matches"]
        assert len(matches) >= 2
        
        # TERM类型应该有更高的权重
        term_match = next((m for m in matches if "销售规则" in m["knowledge_name"]), None)
        logic_match = next((m for m in matches if "销售流程" in m["knowledge_name"]), None)
        
        if term_match and logic_match:
            # 由于TERM权重更高，相同匹配情况下TERM应该分数更高
            assert term_match["similarity_score"] >= logic_match["similarity_score"]