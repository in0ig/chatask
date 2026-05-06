"""
Excel 解析 API 测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.main import app

client = TestClient(app)

class TestExcelParserAPI:
    """Excel 解析 API 测试类"""
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_get_excel_structure_success(self, mock_parser):
        """测试获取 Excel 结构成功"""
        # 准备测试数据
        mock_structure = {
            "file_path": "/test/file.xlsx",
            "sheet_count": 2,
            "sheets": [
                {
                    "name": "Sheet1",
                    "row_count": 100,
                    "column_count": 5,
                    "columns": ["A", "B", "C", "D", "E"],
                    "field_types": [
                        {
                            "field_name": "A",
                            "data_type": "TEXT",
                            "is_nullable": True
                        }
                    ]
                }
            ]
        }
        
        mock_parser.parse_file_structure.return_value = mock_structure
        
        # 执行请求
        response = client.get("/api/excel/structure?file_path=/test/file.xlsx")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_structure
        mock_parser.parse_file_structure.assert_called_once_with("/test/file.xlsx")
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_get_excel_structure_failure(self, mock_parser):
        """测试获取 Excel 结构失败"""
        # 模拟异常
        mock_parser.parse_file_structure.side_effect = Exception("文件不存在")
        
        # 执行请求
        response = client.get("/api/excel/structure?file_path=/invalid/file.xlsx")
        
        # 验证结果
        assert response.status_code == 400
        data = response.json()
        assert "解析 Excel 文件结构失败" in data["detail"]
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_get_sheet_preview_success(self, mock_parser):
        """测试获取 Sheet 预览成功"""
        # 准备测试数据
        mock_preview = {
            "sheet_name": "Sheet1",
            "row_count": 10,
            "column_count": 3,
            "columns": ["Name", "Age", "City"],
            "data": [
                {"Name": "Alice", "Age": 25, "City": "Beijing"},
                {"Name": "Bob", "Age": 30, "City": "Shanghai"}
            ],
            "field_types": [
                {"field_name": "Name", "data_type": "TEXT"},
                {"field_name": "Age", "data_type": "INTEGER"},
                {"field_name": "City", "data_type": "TEXT"}
            ],
            "is_preview": True,
            "preview_limit": 100
        }
        
        mock_parser.get_sheet_preview.return_value = mock_preview
        
        # 执行请求
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx&sheet_name=Sheet1&limit=100")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_preview
        mock_parser.get_sheet_preview.assert_called_once_with("/test/file.xlsx", "Sheet1", 100)
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_get_sheet_preview_with_default_limit(self, mock_parser):
        """测试获取 Sheet 预览使用默认限制"""
        mock_preview = {"sheet_name": "Sheet1", "data": []}
        mock_parser.get_sheet_preview.return_value = mock_preview
        
        # 执行请求（不指定 limit）
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx&sheet_name=Sheet1")
        
        # 验证结果
        assert response.status_code == 200
        mock_parser.get_sheet_preview.assert_called_once_with("/test/file.xlsx", "Sheet1", 100)
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_get_sheet_preview_failure(self, mock_parser):
        """测试获取 Sheet 预览失败"""
        # 模拟异常
        mock_parser.get_sheet_preview.side_effect = Exception("Sheet 不存在")
        
        # 执行请求
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx&sheet_name=InvalidSheet")
        
        # 验证结果
        assert response.status_code == 400
        data = response.json()
        assert "获取 Sheet 预览失败" in data["detail"]
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_validate_sheet_data_success(self, mock_parser):
        """测试验证 Sheet 数据成功"""
        # 准备测试数据
        mock_validation = {
            "sheet_name": "Sheet1",
            "total_rows": 1000,
            "total_columns": 5,
            "field_analysis": [
                {
                    "field_name": "Name",
                    "data_type": "TEXT",
                    "null_percentage": 5.0,
                    "unique_values": 950,
                    "sample_values": ["Alice", "Bob", "Charlie"]
                }
            ],
            "data_quality": {
                "has_empty_rows": False,
                "has_duplicate_headers": False,
                "estimated_data_types": 3
            }
        }
        
        mock_parser.validate_sheet_data.return_value = mock_validation
        
        # 执行请求
        response = client.get("/api/excel/sheet/validate?file_path=/test/file.xlsx&sheet_name=Sheet1")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_validation
        mock_parser.validate_sheet_data.assert_called_once_with("/test/file.xlsx", "Sheet1")
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_validate_sheet_data_failure(self, mock_parser):
        """测试验证 Sheet 数据失败"""
        # 模拟异常
        mock_parser.validate_sheet_data.side_effect = Exception("数据格式错误")
        
        # 执行请求
        response = client.get("/api/excel/sheet/validate?file_path=/test/file.xlsx&sheet_name=Sheet1")
        
        # 验证结果
        assert response.status_code == 400
        data = response.json()
        assert "验证 Sheet 数据失败" in data["detail"]
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_generate_table_schema_success(self, mock_parser):
        """测试生成表结构成功"""
        # 准备测试数据
        mock_schema = {
            "table_name": "user_data",
            "display_name": "Sheet1 (Excel导入)",
            "description": "从 Excel 文件 /test/file.xlsx 的 Sheet1 sheet 导入",
            "data_mode": "IMPORT",
            "fields": [
                {
                    "field_name": "name",
                    "display_name": "Name",
                    "data_type": "VARCHAR(255)",
                    "is_nullable": True,
                    "is_primary_key": False,
                    "sort_order": 1,
                    "description": "从 Excel 导入的字段: Name"
                }
            ]
        }
        
        mock_parser.generate_table_schema.return_value = mock_schema
        
        # 执行请求
        response = client.post("/api/excel/generate-schema?file_path=/test/file.xlsx&sheet_name=Sheet1&table_name=user_data")
        
        # 验证结果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] == mock_schema
        mock_parser.generate_table_schema.assert_called_once_with("/test/file.xlsx", "Sheet1", "user_data")
    
    @patch('src.api.excel_parser_api.excel_parser')
    def test_generate_table_schema_failure(self, mock_parser):
        """测试生成表结构失败"""
        # 模拟异常
        mock_parser.generate_table_schema.side_effect = Exception("无法生成表结构")
        
        # 执行请求
        response = client.post("/api/excel/generate-schema?file_path=/test/file.xlsx&sheet_name=Sheet1&table_name=user_data")
        
        # 验证结果
        assert response.status_code == 400
        data = response.json()
        assert "生成表结构失败" in data["detail"]
    
    def test_missing_required_parameters(self):
        """测试缺少必需参数"""
        # 测试缺少 file_path 参数
        response = client.get("/api/excel/structure")
        assert response.status_code == 422  # FastAPI 参数验证错误
        
        # 测试缺少 sheet_name 参数
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx")
        assert response.status_code == 422
    
    def test_invalid_limit_parameter(self):
        """测试无效的 limit 参数"""
        # 测试 limit 小于 1
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx&sheet_name=Sheet1&limit=0")
        assert response.status_code == 422
        
        # 测试 limit 大于 1000
        response = client.get("/api/excel/sheet/preview?file_path=/test/file.xlsx&sheet_name=Sheet1&limit=1001")
        assert response.status_code == 422