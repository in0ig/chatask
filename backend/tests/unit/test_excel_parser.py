"""
Excel 解析器服务测试
"""

import pytest
from unittest.mock import Mock, patch
from src.services.excel_parser import ExcelParser

class TestExcelParser:
    """Excel 解析器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.parser = ExcelParser()
    
    @patch('src.services.excel_parser.ExcelService')
    def test_parse_file_structure_success(self, mock_excel_service_class):
        """测试解析文件结构成功"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 准备测试数据
        mock_structure = {
            "file_path": "/test/file.xlsx",
            "sheet_count": 1,
            "sheets": [
                {
                    "name": "Sheet1",
                    "row_count": 100,
                    "column_count": 3,
                    "columns": ["Name", "Age", "City"]
                }
            ]
        }
        
        mock_field_types = [
            {
                "field_name": "Name",
                "data_type": "TEXT",
                "is_nullable": True,
                "sample_values": ["Alice", "Bob"],
                "unique_count": 95,
                "null_count": 5
            },
            {
                "field_name": "Age", 
                "data_type": "INTEGER",
                "is_nullable": False,
                "sample_values": [25, 30, 35],
                "unique_count": 50,
                "null_count": 0
            }
        ]
        
        mock_excel_service.get_excel_structure.return_value = mock_structure
        mock_excel_service.infer_field_types.return_value = mock_field_types
        
        # 重新创建解析器以使用 Mock
        parser = ExcelParser()
        
        # 执行测试
        result = parser.parse_file_structure("/test/file.xlsx")
        
        # 验证结果
        assert result["file_path"] == "/test/file.xlsx"
        assert result["sheet_count"] == 1
        assert len(result["sheets"]) == 1
        assert result["sheets"][0]["field_types"] == mock_field_types
        
        # 验证调用
        mock_excel_service.get_excel_structure.assert_called_once_with("/test/file.xlsx")
        mock_excel_service.infer_field_types.assert_called_once_with("/test/file.xlsx", "Sheet1")
    
    @patch('src.services.excel_parser.ExcelService')
    def test_parse_file_structure_failure(self, mock_excel_service_class):
        """测试解析文件结构失败"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 模拟异常
        mock_excel_service.get_excel_structure.side_effect = Exception("文件不存在")
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试并验证异常
        with pytest.raises(Exception) as exc_info:
            parser.parse_file_structure("/invalid/file.xlsx")
        
        assert "Failed to parse Excel structure" in str(exc_info.value)
    
    @patch('src.services.excel_parser.ExcelService')
    def test_get_sheet_preview_success(self, mock_excel_service_class):
        """测试获取 Sheet 预览成功"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 准备测试数据
        mock_sheet_data = {
            "sheet_name": "Sheet1",
            "row_count": 10,
            "column_count": 2,
            "columns": ["Name", "Age"],
            "data": [
                {"Name": "Alice", "Age": 25},
                {"Name": "Bob", "Age": 30}
            ]
        }
        
        mock_field_types = [
            {"field_name": "Name", "data_type": "TEXT"},
            {"field_name": "Age", "data_type": "INTEGER"}
        ]
        
        mock_excel_service.get_sheet_data.return_value = mock_sheet_data
        mock_excel_service.infer_field_types.return_value = mock_field_types
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试
        result = parser.get_sheet_preview("/test/file.xlsx", "Sheet1", 100)
        
        # 验证结果
        assert result["sheet_name"] == "Sheet1"
        assert result["field_types"] == mock_field_types
        assert result["is_preview"] is True
        assert result["preview_limit"] == 100
        assert result["data"] == mock_sheet_data["data"]
        
        # 验证调用
        mock_excel_service.get_sheet_data.assert_called_once_with("/test/file.xlsx", "Sheet1", 100)
        mock_excel_service.infer_field_types.assert_called_once_with("/test/file.xlsx", "Sheet1")
    
    @patch('src.services.excel_parser.ExcelService')
    def test_get_sheet_preview_failure(self, mock_excel_service_class):
        """测试获取 Sheet 预览失败"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 模拟异常
        mock_excel_service.get_sheet_data.side_effect = Exception("Sheet 不存在")
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试并验证异常
        with pytest.raises(Exception) as exc_info:
            parser.get_sheet_preview("/test/file.xlsx", "InvalidSheet", 100)
        
        assert "Failed to get sheet preview" in str(exc_info.value)
    
    @patch('src.services.excel_parser.ExcelService')
    def test_validate_sheet_data_success(self, mock_excel_service_class):
        """测试验证 Sheet 数据成功"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 准备测试数据
        mock_field_types = [
            {
                "field_name": "Name",
                "data_type": "TEXT",
                "unique_count": 95,
                "null_count": 5,
                "sample_values": ["Alice", "Bob"]
            }
        ]
        
        mock_sheet_data = {
            "row_count": 100,
            "column_count": 1
        }
        
        mock_excel_service.infer_field_types.return_value = mock_field_types
        mock_excel_service.get_sheet_data.return_value = mock_sheet_data
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试
        result = parser.validate_sheet_data("/test/file.xlsx", "Sheet1")
        
        # 验证结果
        assert result["sheet_name"] == "Sheet1"
        assert result["total_rows"] == 100
        assert result["total_columns"] == 1
        assert len(result["field_analysis"]) == 1
        
        field_analysis = result["field_analysis"][0]
        assert field_analysis["field_name"] == "Name"
        assert field_analysis["data_type"] == "TEXT"
        assert field_analysis["null_percentage"] == 5.0
        assert field_analysis["unique_values"] == 95
        
        # 验证数据质量指标
        assert "data_quality" in result
        assert result["data_quality"]["has_duplicate_headers"] is False
        
        # 验证调用
        mock_excel_service.infer_field_types.assert_called_once_with("/test/file.xlsx", "Sheet1")
        mock_excel_service.get_sheet_data.assert_called_once_with("/test/file.xlsx", "Sheet1", limit=1000)
    
    @patch('src.services.excel_parser.ExcelService')
    def test_validate_sheet_data_with_duplicate_headers(self, mock_excel_service_class):
        """测试验证包含重复列名的 Sheet 数据"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 准备测试数据（包含重复列名）
        mock_field_types = [
            {"field_name": "Name", "data_type": "TEXT", "unique_count": 50, "null_count": 0, "sample_values": []},
            {"field_name": "Name", "data_type": "TEXT", "unique_count": 30, "null_count": 5, "sample_values": []}  # 重复列名
        ]
        
        mock_sheet_data = {"row_count": 100, "column_count": 2}
        
        mock_excel_service.infer_field_types.return_value = mock_field_types
        mock_excel_service.get_sheet_data.return_value = mock_sheet_data
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试
        result = parser.validate_sheet_data("/test/file.xlsx", "Sheet1")
        
        # 验证结果
        assert result["data_quality"]["has_duplicate_headers"] is True
    
    @patch('src.services.excel_parser.ExcelService')
    def test_generate_table_schema_success(self, mock_excel_service_class):
        """测试生成表结构成功"""
        # 准备 Mock 对象
        mock_excel_service = Mock()
        mock_excel_service_class.return_value = mock_excel_service
        
        # 准备测试数据
        mock_field_types = [
            {
                "field_name": "User Name",  # 包含空格和特殊字符
                "data_type": "TEXT",
                "is_nullable": True
            },
            {
                "field_name": "Age",
                "data_type": "INTEGER", 
                "is_nullable": False
            },
            {
                "field_name": "123Invalid",  # 以数字开头
                "data_type": "DECIMAL",
                "is_nullable": True
            }
        ]
        
        mock_excel_service.infer_field_types.return_value = mock_field_types
        
        # 重新创建解析器
        parser = ExcelParser()
        
        # 执行测试
        result = parser.generate_table_schema("/test/file.xlsx", "Sheet1", "user_data")
        
        # 验证结果
        assert result["table_name"] == "user_data"
        assert result["display_name"] == "Sheet1 (Excel导入)"
        assert result["data_mode"] == "IMPORT"
        assert len(result["fields"]) == 3
        
        # 验证字段处理
        fields = result["fields"]
        
        # 第一个字段：空格被替换为下划线
        assert fields[0]["field_name"] == "User_Name"
        assert fields[0]["display_name"] == "User Name"
        assert fields[0]["data_type"] == "VARCHAR(255)"
        assert fields[0]["is_nullable"] is True
        assert fields[0]["sort_order"] == 1
        
        # 第二个字段：正常字段
        assert fields[1]["field_name"] == "Age"
        assert fields[1]["data_type"] == "INT"
        assert fields[1]["is_nullable"] is False
        
        # 第三个字段：以数字开头，添加前缀
        assert fields[2]["field_name"] == "col_123Invalid"
        assert fields[2]["data_type"] == "DECIMAL(10,2)"
        
        # 验证调用
        mock_excel_service.infer_field_types.assert_called_once_with("/test/file.xlsx", "Sheet1")
    
    def test_sanitize_field_name(self):
        """测试字段名清理功能"""
        parser = ExcelParser()
        
        # 测试正常字段名
        assert parser._sanitize_field_name("name") == "name"
        assert parser._sanitize_field_name("user_name") == "user_name"
        
        # 测试包含空格的字段名
        assert parser._sanitize_field_name("user name") == "user_name"
        
        # 测试包含特殊字符的字段名
        assert parser._sanitize_field_name("user-name@test") == "user_name_test"
        
        # 测试以数字开头的字段名
        assert parser._sanitize_field_name("123name") == "col_123name"
        
        # 测试空字段名
        assert parser._sanitize_field_name("") == "unnamed_column"
        assert parser._sanitize_field_name(None) == "unnamed_column"
        
        # 测试中文字段名
        assert parser._sanitize_field_name("用户名称") == "用户名称"
        assert parser._sanitize_field_name("用户-名称") == "用户_名称"
    
    def test_map_to_db_type(self):
        """测试数据类型映射"""
        parser = ExcelParser()
        
        # 测试已知类型
        assert parser._map_to_db_type("TEXT") == "VARCHAR(255)"
        assert parser._map_to_db_type("INTEGER") == "INT"
        assert parser._map_to_db_type("DECIMAL") == "DECIMAL(10,2)"
        assert parser._map_to_db_type("DATETIME") == "DATETIME"
        assert parser._map_to_db_type("BOOLEAN") == "BOOLEAN"
        
        # 测试未知类型，应该返回默认值
        assert parser._map_to_db_type("UNKNOWN") == "VARCHAR(255)"
        assert parser._map_to_db_type("") == "VARCHAR(255)"
        assert parser._map_to_db_type(None) == "VARCHAR(255)"