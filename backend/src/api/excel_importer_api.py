"""
Excel 导入 API
提供 Excel 文件导入相关的接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Depends, UploadFile, Form
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from pydantic import BaseModel
from src.services.excel_importer import ExcelImporter
from src.database import get_db
from sqlalchemy.orm import Session
import os

# 创建路由器
router = APIRouter(prefix="/api/data-tables", tags=["Excel导入"])

# 创建日志记录器
logger = logging.getLogger(__name__)

# 响应模型
class ImportJobResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# 导入状态响应模型
class ImportStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: float
    message: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None

# 后台任务处理函数
def process_excel_import(
    job_id: str,
    file_path: str,
    table_name: str,
    sheet_name: Optional[str],
    header_row: int,
    start_row: int,
    data_type_mapping: Optional[Dict[str, str]],
    create_table: bool,
    replace_existing: bool,
    db: Session
):
    """
    处理 Excel 导入的后台任务
    """
    try:
        logger.info(f"Starting Excel import job {job_id}: {file_path} -> {table_name}")
        
        # 创建 ExcelImporter 实例以执行导入操作
        excel_importer = ExcelImporter(db)
        result = excel_importer.import_excel_data(
            file_path=file_path,
            table_name=table_name,
            sheet_name=sheet_name,
            job_id=job_id
        )
        logger.info(f"Excel import job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Excel import job {job_id} failed: {str(e)}", exc_info=True)
        # import_excel_data 方法已自动处理失败状态，无需手动更新
        raise

@router.post("/import-excel", response_model=ImportJobResponse)
async def import_excel(
    file: UploadFile,
    table_name: str = Form(...),
    sheet_name: Optional[str] = Form(None),
    header_row: Optional[int] = Form(1),
    start_row: Optional[int] = Form(2),
    create_table: Optional[bool] = Form(True),
    replace_existing: Optional[bool] = Form(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    异步导入 Excel 文件到数据表
    
    Args:
        file: Excel 文件上传
        table_name: 目标表名
        sheet_name: 指定的 Sheet 名称（可选）
        header_row: 表头行号（从1开始，默认1）
        start_row: 数据开始行号（从1开始，默认2）
        create_table: 是否自动创建表（默认True）
        replace_existing: 是否替换已存在的表（默认False）
        
    Returns:
        导入任务的作业ID和状态
    """
    logger.info(f"API: Starting Excel import job with file: {file.filename}")
    
    try:
        # 验证文件扩展名
        if not file.filename or not file.filename.lower().endswith(('.xlsx', '.xls')):
            logger.warning(f"Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail="仅支持 .xlsx 和 .xls 文件格式"
            )
        
        # 验证表名是否有效
        if not table_name or not table_name.strip():
            logger.warning("Table name is empty or invalid")
            raise HTTPException(
                status_code=422, 
                detail="表名不能为空"
            )
        
        # 创建临时文件保存上传的Excel文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx" if file.filename.lower().endswith('.xlsx') else ".xls") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # 创建 ExcelImporter 实例并直接调用导入方法
        excel_importer = ExcelImporter(db)
        job_id = f"import_{int(datetime.now().timestamp())}_{hash(tmp_file_path + table_name)}"
        
        # 直接调用 import_excel_data 方法，该方法会自动处理进度跟踪
        result = excel_importer.import_excel_data(
            file_path=tmp_file_path,
            table_name=table_name,
            sheet_name=sheet_name,
            job_id=job_id
        )
        
        # 添加后台任务以清理临时文件
        background_tasks.add_task(
            lambda: os.unlink(tmp_file_path)
        )
        
        # 添加后台任务以处理导入（虽然我们已经直接调用了，但为了保持异步，仍保留）
        background_tasks.add_task(
            process_excel_import,
            job_id,
            tmp_file_path,
            table_name,
            sheet_name,
            header_row,
            start_row,
            None,  # data_type_mapping 不再通过参数传递
            create_table,
            replace_existing,
            db
        )
        
        # 返回作业信息
        response = ImportJobResponse(
            job_id=job_id,
            status="pending",
            progress=0.0,
            created_at=datetime.now()
        )
        
        logger.info(f"Excel import job {job_id} created successfully")
        return response
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"Failed to create Excel import job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"创建导入任务失败: {str(e)}"
        )

@router.get("/import-status/{job_id}", response_model=ImportStatusResponse)
async def get_import_status(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    获取 Excel 导入任务的状态
    
    Args:
        job_id: 导入任务的作业ID
        
    Returns:
        导入任务的详细状态信息
    """
    logger.info(f"API: Getting import status for job {job_id}")
    
    # 获取作业状态
    excel_importer = ExcelImporter(db)
    status_info = excel_importer.get_import_progress(job_id)
    
    if not status_info:
        logger.warning(f"Import job {job_id} not found")
        raise HTTPException(
            status_code=404, 
            detail=f"导入任务不存在: {job_id}"
        )
    
    # 构建响应
    # 将 start_time 字符串转换为 datetime 对象，如果为 None 则保持 None
    created_at = datetime.fromisoformat(status_info["start_time"]) if status_info["start_time"] is not None else None
    
    # 将 end_time 字符串转换为 datetime 对象，如果为 None 则保持 None
    completed_at = datetime.fromisoformat(status_info["end_time"]) if status_info["end_time"] is not None else None
    
    # 将 errors 列表转换为字典格式，如果为空则设为 None
    error_details = {"errors": status_info.get("errors")} if status_info.get("errors") and len(status_info.get("errors")) > 0 else None
    
    # 构建响应
    response = ImportStatusResponse(
        job_id=status_info["job_id"],
        status=status_info["status"],
        progress=status_info["progress_percent"],
        message=status_info.get("errors")[0] if status_info.get("errors") and len(status_info.get("errors")) > 0 else None,
        created_at=created_at,
        completed_at=completed_at,
        result=status_info.get("result"),
        error_details=error_details
    )
    
    logger.info(f"Import job {job_id} status retrieved successfully")
    return response

# 可选：取消导入任务的端点
@router.post("/import-cancel/{job_id}")
async def cancel_import_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """
    取消正在进行的 Excel 导入任务
    
    Args:
        job_id: 导入任务的作业ID
        db: 数据库会话依赖，用于与数据库交互
        
    Returns:
        取消结果
    """
    logger.info(f"API: Canceling import job {job_id}")
    
    try:
        # 检查任务是否存在（通过获取进度信息）
        excel_importer = ExcelImporter(db)
        status_info = excel_importer.get_import_progress(job_id)
        
        if not status_info:
            logger.warning(f"Import job {job_id} not found for cancellation")
            raise HTTPException(
                status_code=404, 
                detail=f"导入任务不存在: {job_id}"
            )
        
        # 检查任务是否已完成
        if status_info["status"] in ["completed", "failed"]:
            logger.warning(f"Cannot cancel completed or failed job {job_id}")
            raise HTTPException(
                status_code=400, 
                detail=f"已完成或失败的任务无法取消: {job_id}"
            )
        
        # 取消任务
        success = excel_importer.cancel_job(job_id)
        
        if success:
            logger.info(f"Import job {job_id} cancelled successfully")
            return {"success": True, "message": f"导入任务 {job_id} 已取消"}
        else:
            logger.warning(f"Failed to cancel import job {job_id}")
            raise HTTPException(
                status_code=500, 
                detail=f"取消导入任务失败: {job_id}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel import job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"取消导入任务失败: {str(e)}"
        )
