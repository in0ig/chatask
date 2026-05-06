"""
Excel 解析 API
提供 Excel 文件解析相关的接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging
from src.services.excel_parser import ExcelParser

# 创建路由器
router = APIRouter(prefix="/api/excel", tags=["Excel解析"])

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建 Excel 解析器实例
excel_parser = ExcelParser()

@router.get("/structure")
async def get_excel_structure(
    file_path: str = Query(..., description="Excel 文件路径")
) -> Dict[str, Any]:
    """
    获取 Excel 文件结构
    
    Args:
        file_path: Excel 文件路径
        
    Returns:
        Excel 文件结构信息，包括所有 Sheet 和字段类型
    """
    logger.info(f"API: Getting Excel structure for {file_path}")
    
    try:
        structure = excel_parser.parse_file_structure(file_path)
        logger.info(f"API: Excel structure retrieved successfully")
        return {
            "success": True,
            "data": structure
        }
    except Exception as e:
        logger.error(f"API: Failed to get Excel structure: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"解析 Excel 文件结构失败: {str(e)}"
        )

@router.get("/sheet/preview")
async def get_sheet_preview(
    file_path: str = Query(..., description="Excel 文件路径"),
    sheet_name: str = Query(..., description="Sheet 名称"),
    limit: int = Query(100, description="预览行数限制", ge=1, le=1000)
) -> Dict[str, Any]:
    """
    获取指定 Sheet 的预览数据
    
    Args:
        file_path: Excel 文件路径
        sheet_name: Sheet 名称
        limit: 预览行数限制
        
    Returns:
        Sheet 预览数据
    """
    logger.info(f"API: Getting sheet preview for {file_path}:{sheet_name}, limit={limit}")
    
    try:
        preview = excel_parser.get_sheet_preview(file_path, sheet_name, limit)
        logger.info(f"API: Sheet preview retrieved successfully")
        return {
            "success": True,
            "data": preview
        }
    except Exception as e:
        logger.error(f"API: Failed to get sheet preview: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"获取 Sheet 预览失败: {str(e)}"
        )

@router.get("/sheet/validate")
async def validate_sheet_data(
    file_path: str = Query(..., description="Excel 文件路径"),
    sheet_name: str = Query(..., description="Sheet 名称")
) -> Dict[str, Any]:
    """
    验证 Sheet 数据质量
    
    Args:
        file_path: Excel 文件路径
        sheet_name: Sheet 名称
        
    Returns:
        数据质量验证结果
    """
    logger.info(f"API: Validating sheet data for {file_path}:{sheet_name}")
    
    try:
        validation = excel_parser.validate_sheet_data(file_path, sheet_name)
        logger.info(f"API: Sheet data validation completed")
        return {
            "success": True,
            "data": validation
        }
    except Exception as e:
        logger.error(f"API: Failed to validate sheet data: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"验证 Sheet 数据失败: {str(e)}"
        )

@router.post("/generate-schema")
async def generate_table_schema(
    file_path: str = Query(..., description="Excel 文件路径"),
    sheet_name: str = Query(..., description="Sheet 名称"),
    table_name: str = Query(..., description="目标表名")
) -> Dict[str, Any]:
    """
    根据 Excel 数据生成数据库表结构
    
    Args:
        file_path: Excel 文件路径
        sheet_name: Sheet 名称
        table_name: 目标表名
        
    Returns:
        生成的表结构定义
    """
    logger.info(f"API: Generating table schema for {file_path}:{sheet_name} -> {table_name}")
    
    try:
        schema = excel_parser.generate_table_schema(file_path, sheet_name, table_name)
        logger.info(f"API: Table schema generated successfully")
        return {
            "success": True,
            "data": schema
        }
    except Exception as e:
        logger.error(f"API: Failed to generate table schema: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"生成表结构失败: {str(e)}"
        )