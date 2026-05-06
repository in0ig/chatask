"""
表字段配置API端点
实现表字段的查询和配置功能
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from src.models.data_preparation_model import DataTable, TableField
from src.schemas.data_table_schema import TableFieldResponse, TableFieldUpdate
from src.database import get_db

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Table Fields"])

@router.get("/data-tables/{table_id}/fields", response_model=List[TableFieldResponse])
async def get_table_fields(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定数据表的所有字段列表
    
    返回字段的详细配置信息，包括显示名称、数据类型、字典关联等
    """
    logger.info(f"Getting fields for table ID: {table_id}")
    
    # 检查数据表是否存在
    table = db.query(DataTable).filter(DataTable.id == table_id).first()
    if not table:
        logger.warning(f"Data table with ID {table_id} not found")
        raise HTTPException(status_code=404, detail=f"数据表不存在: {table_id}")
    
    # 获取字段列表
    fields = db.query(TableField).filter(
        TableField.table_id == table_id
    ).order_by(TableField.sort_order, TableField.field_name).all()
    
    logger.info(f"Found {len(fields)} fields for table {table_id}")
    return fields

@router.put("/table-fields/{field_id}", response_model=TableFieldResponse)
async def update_table_field(
    field_id: str,
    field_update: TableFieldUpdate,
    db: Session = Depends(get_db)
):
    """
    更新表字段配置
    
    支持更新字段的显示名称、描述、字典关联、查询属性等配置
    """
    logger.info(f"Updating field ID: {field_id}")
    
    # 获取字段
    field = db.query(TableField).filter(TableField.id == field_id).first()
    if not field:
        logger.warning(f"Table field with ID {field_id} not found")
        raise HTTPException(status_code=404, detail=f"字段不存在: {field_id}")
    
    # 更新字段配置
    update_data = field_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(field, key, value)
    
    try:
        db.commit()
        db.refresh(field)
        logger.info(f"Successfully updated field {field_id}")
        return field
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update field {field_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="更新字段配置失败")