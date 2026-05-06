from fastapi import APIRouter, File, UploadFile, HTTPException, status
from typing import List, Dict, Any
import os
import logging
from pydantic import BaseModel
import pandas as pd
from src.services.excel_service import ExcelService

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建API路由
router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])

# 定义响应模型
class ExcelFileInfo(BaseModel):
    filename: str
    file_path: str
    sheet_names: List[str]
    row_count: int
    column_count: int

@router.post("/upload-excel", response_model=ExcelFileInfo)
async def upload_excel(file: UploadFile = File(...)):
    """
    上传Excel文件
    
    - 限制文件大小为20MB
    - 只允许 .xlsx 和 .xls 格式
    - 使用ExcelService解析文件
    - 返回文件信息和Sheet列表
    """
    logger.info(f"Received file upload request: {file.filename}")
    
    # 验证文件格式
    allowed_extensions = {".xlsx", ".xls"}
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        error_msg = f"Invalid file format: {file.filename}. Only .xlsx and .xls files are allowed."
        logger.warning(error_msg)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # 检查文件大小（20MB）
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB
        error_msg = "File size exceeds 20MB limit."
        logger.warning(error_msg)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_msg
        )
    
    # 重置文件指针以便ExcelService可以读取
    file.file.seek(0)
    
    try:
        # 使用ExcelService保存文件
        excel_service = ExcelService()
        file_path = excel_service.save_uploaded_file(file)
        
        # 使用pandas读取Excel文件获取sheet信息
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        # 获取行数和列数（使用第一个sheet）
        if len(sheet_names) > 0:
            df = pd.read_excel(file_path, sheet_name=sheet_names[0])
            row_count = len(df)
            column_count = len(df.columns)
        else:
            row_count = 0
            column_count = 0
        
        # 返回文件信息
        return ExcelFileInfo(
            filename=file.filename,
            file_path=file_path,
            sheet_names=sheet_names,
            row_count=row_count,
            column_count=column_count
        )
        
    except Exception as e:
        error_msg = f"Failed to process uploaded file {file.filename}: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

# 导出路由器
__all__ = ["router"]
