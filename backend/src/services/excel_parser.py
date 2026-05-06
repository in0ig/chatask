from typing import Dict, List, Any, Optional
import logging
from .excel_service import ExcelService

logger = logging.getLogger(__name__)

class ExcelParser:
    """
    Excel 解析器，提供高级的 Excel 文件解析功能
    """
    
    def __init__(self):
        self.excel_service = ExcelService()
        logger.info("ExcelParser initialized")
    
    def parse_file_structure(self, file_path: str) -> Dict[str, Any]:
        """
        解析 Excel 文件结构
        返回文件的完整结构信息
        """
        logger.info(f"Parsing Excel file structure: {file_path}")
        
        try:
            structure = self.excel_service.get_excel_structure(file_path)
            
            # 为每个 sheet 添加字段类型推断
            for sheet in structure["sheets"]:
                sheet_name = sheet["name"]
                field_types = self.excel_service.infer_field_types(file_path, sheet_name)
                sheet["field_types"] = field_types
            
            logger.info(f"Excel structure parsed successfully: {structure['sheet_count']} sheets")
            return structure
            
        except Exception as e:
            error_msg = f"Failed to parse Excel structure: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def get_sheet_preview(self, file_path: str, sheet_name: str, limit: int = 100) -> Dict[str, Any]:
        """
        获取指定 Sheet 的预览数据
        """
        logger.info(f"Getting sheet preview: {file_path}, sheet: {sheet_name}, limit: {limit}")
        
        try:
            sheet_data = self.excel_service.get_sheet_data(file_path, sheet_name, limit)
            field_types = self.excel_service.infer_field_types(file_path, sheet_name)
            
            result = {
                **sheet_data,
                "field_types": field_types,
                "is_preview": True,
                "preview_limit": limit
            }
            
            logger.info(f"Sheet preview generated successfully: {len(sheet_data['data'])} rows")
            return result
            
        except Exception as e:
            error_msg = f"Failed to get sheet preview: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def validate_sheet_data(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """
        验证 Sheet 数据的质量
        """
        logger.info(f"Validating sheet data: {file_path}, sheet: {sheet_name}")
        
        try:
            field_types = self.excel_service.infer_field_types(file_path, sheet_name)
            sheet_data = self.excel_service.get_sheet_data(file_path, sheet_name, limit=1000)  # 取样验证
            
            validation_result = {
                "sheet_name": sheet_name,
                "total_rows": sheet_data["row_count"],
                "total_columns": sheet_data["column_count"],
                "field_analysis": [],
                "data_quality": {
                    "has_empty_rows": False,
                    "has_duplicate_headers": False,
                    "estimated_data_types": len(set(ft["data_type"] for ft in field_types))
                }
            }
            
            # 分析每个字段
            for field_type in field_types:
                field_analysis = {
                    "field_name": field_type["field_name"],
                    "data_type": field_type["data_type"],
                    "null_percentage": round((field_type["null_count"] / sheet_data["row_count"]) * 100, 2) if sheet_data["row_count"] > 0 else 0,
                    "unique_values": field_type["unique_count"],
                    "sample_values": field_type["sample_values"]
                }
                validation_result["field_analysis"].append(field_analysis)
            
            # 检查重复的列名
            column_names = [ft["field_name"] for ft in field_types]
            if len(column_names) != len(set(column_names)):
                validation_result["data_quality"]["has_duplicate_headers"] = True
            
            logger.info(f"Sheet data validation completed")
            return validation_result
            
        except Exception as e:
            error_msg = f"Failed to validate sheet data: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def generate_table_schema(self, file_path: str, sheet_name: str, table_name: str) -> Dict[str, Any]:
        """
        根据 Excel 数据生成数据库表结构
        """
        logger.info(f"Generating table schema: {file_path}, sheet: {sheet_name}, table: {table_name}")
        
        try:
            field_types = self.excel_service.infer_field_types(file_path, sheet_name)
            
            # 生成数据库字段定义
            fields = []
            for i, field_type in enumerate(field_types):
                field_name = self._sanitize_field_name(field_type["field_name"])
                db_type = self._map_to_db_type(field_type["data_type"])
                
                field_def = {
                    "field_name": field_name,
                    "display_name": field_type["field_name"],
                    "data_type": db_type,
                    "is_nullable": field_type["is_nullable"],
                    "is_primary_key": False,  # Excel 导入的表通常没有主键
                    "sort_order": i + 1,
                    "description": f"从 Excel 导入的字段: {field_type['field_name']}"
                }
                fields.append(field_def)
            
            schema = {
                "table_name": table_name,
                "display_name": f"{sheet_name} (Excel导入)",
                "description": f"从 Excel 文件 {file_path} 的 {sheet_name} sheet 导入",
                "data_mode": "IMPORT",
                "fields": fields
            }
            
            logger.info(f"Table schema generated: {len(fields)} fields")
            return schema
            
        except Exception as e:
            error_msg = f"Failed to generate table schema: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def _sanitize_field_name(self, field_name: str) -> str:
        """
        清理字段名，使其符合数据库命名规范
        """
        import re
        # 在调用 str() 之前检查 None 值
        if field_name is None:
            return 'unnamed_column'
        # 移除特殊字符，只保留字母、数字和下划线
        sanitized = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', str(field_name))
        # 确保不以数字开头
        if sanitized and sanitized[0].isdigit():
            sanitized = f"col_{sanitized}"
        # 如果为空，使用默认名称
        if not sanitized:
            sanitized = "unnamed_column"
        return sanitized
    
    def _map_to_db_type(self, excel_type: str) -> str:
        """
        将 Excel 推断的类型映射到数据库类型
        """
        type_mapping = {
            "TEXT": "VARCHAR(255)",
            "INTEGER": "INT",
            "DECIMAL": "DECIMAL(10,2)",
            "DATETIME": "DATETIME",
            "BOOLEAN": "BOOLEAN"
        }
        return type_mapping.get(excel_type, "VARCHAR(255)")