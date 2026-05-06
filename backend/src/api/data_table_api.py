"""
数据表API端点
实现数据表的CRUD功能
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.schemas.data_table_schema import (
    DataTableCreate,
    DataTableUpdate,
    DataTableResponse,
    DataTableListResponse,
    DataTableDetailResponse,
    FieldWithDictionaryResponse,
    TableRelationResponse,
    DictionarySimple,
    DictionaryItemSimple
)
from src.services.data_table_service import DataTableService
from src.services.table_discovery_service import TableDiscoveryService
from src.database import get_db
from src.services.async_sync import task_manager, async_table_sync_task, SyncTaskStatus

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(tags=["数据表管理"])

data_table_service = DataTableService()
table_discovery_service = TableDiscoveryService()

@router.get("/", response_model=DataTableListResponse)
async def get_data_tables(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1-100"),
    search: Optional[str] = Query(None, description="搜索关键词（表名）"),
    source_id: Optional[str] = Query(None, description="数据源ID，用于筛选"),
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    db: Session = Depends(get_db)
):
    """
    获取数据表列表
    
    支持分页、搜索、按数据源筛选功能
    """
    logger.info(f"Retrieving data tables with filters - page: {page}, page_size: {page_size}, search: {search}, source_id: {source_id}, status: {status}")
    
    try:
        # 调用服务层获取数据表列表
        tables_response = data_table_service.get_all_tables(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            source_id=source_id,
            status=status
        )
        
        logger.info(f"Retrieved {len(tables_response.items)} data tables out of {tables_response.total} total")
        return tables_response
        
    except Exception as e:
        logger.error(f"Failed to retrieve data tables: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据表列表失败")


@router.post("/", response_model=DataTableResponse, status_code=201)
async def create_data_table(
    table_data: DataTableCreate,
    db: Session = Depends(get_db)
):
    """
    创建数据表
    
    - 验证数据源是否存在
    - 验证表名唯一性
    - 支持所有字段的创建
    """
    logger.info(f"Creating new data table: {table_data.table_name} for source {table_data.source_id}")
    
    try:
        # 验证数据源是否存在
        source = db.query(DataSource).filter(DataSource.id == table_data.source_id).first()
        if not source:
            logger.warning(f"Data source with ID {table_data.source_id} not found")
            raise HTTPException(
                status_code=404, 
                detail=f"数据源不存在: {table_data.source_id}"
            )
        
        # 验证表名在该数据源下是否唯一
        existing_table = data_table_service.get_table_by_name_and_source(db, table_data.table_name, table_data.source_id)
        if existing_table:
            logger.warning(f"Data table with name {table_data.table_name} already exists for source {table_data.source_id}")
            raise HTTPException(
                status_code=409, 
                detail=f"数据源 {table_data.source_id} 下已存在同名表: {table_data.table_name}"
            )
        
        # 创建数据表
        db_table = data_table_service.create_table(db, table_data)
        
        # 转换为响应模型
        table_dict = db_table.to_dict()
        logger.info(f"Data table created successfully: {table_data.table_name} (ID: {db_table.id})")
        return DataTableResponse(**table_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error creating data table: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error creating data table: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create data table: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建数据表失败")


@router.get("/{table_id}", response_model=DataTableResponse)
async def get_data_table_by_id(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的数据表详情
    """
    logger.info(f"Retrieving data table details for ID: {table_id}")
    
    try:
        table = data_table_service.get_table_by_id(db, table_id)
        
        if not table:
            logger.warning(f"Data table with ID {table_id} not found")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 转换为响应模型
        table_dict = table.to_dict()
        logger.info(f"Retrieved data table details for ID: {table_id}")
        return DataTableResponse(**table_dict)
        
    except HTTPException:
        # 重新抛出HTTP异常，不要转换为500错误
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve data table {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据表详情失败")


@router.get("/{table_id}/detail", response_model=DataTableDetailResponse)
async def get_data_table_detail(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    获取数据表完整详情（包含字段、数据字典、表关联关系）
    
    返回信息包括：
    - 表基本信息
    - 字段列表（包含字段描述和关联的数据字典详情）
    - 表与表之间的关联关系
    """
    logger.info(f"Retrieving detailed data table information for ID: {table_id}")
    
    try:
        from src.models.data_preparation_model import TableField, Dictionary, DictionaryItem, TableRelation
        
        # 获取表基本信息
        table = data_table_service.get_table_by_id(db, table_id)
        
        if not table:
            logger.warning(f"Data table with ID {table_id} not found")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 获取字段列表（包含数据字典信息）
        fields_with_dict = []
        fields = db.query(TableField).filter(TableField.table_id == table_id).order_by(TableField.sort_order, TableField.field_name).all()
        
        for field in fields:
            field_dict = {
                "id": field.id,
                "table_id": field.table_id,
                "field_name": field.field_name,
                "display_name": field.display_name,
                "data_type": field.data_type,
                "description": field.description,
                "is_primary_key": field.is_primary_key,
                "is_nullable": field.is_nullable,
                "default_value": field.default_value,
                "dictionary_id": field.dictionary_id,
                "dictionary": None,
                "is_queryable": field.is_queryable,
                "is_aggregatable": field.is_aggregatable,
                "sort_order": field.sort_order
            }
            
            # 如果字段关联了数据字典，获取字典详情
            if field.dictionary_id:
                dictionary = db.query(Dictionary).filter(Dictionary.id == field.dictionary_id).first()
                if dictionary:
                    # 获取字典项
                    dict_items = db.query(DictionaryItem).filter(
                        DictionaryItem.dictionary_id == dictionary.id,
                        DictionaryItem.status == True
                    ).order_by(DictionaryItem.sort_order).all()
                    
                    field_dict["dictionary"] = {
                        "id": dictionary.id,
                        "code": dictionary.code,
                        "name": dictionary.name,
                        "items": [
                            {
                                "item_key": item.item_key,
                                "item_value": item.item_value,
                                "description": item.description
                            }
                            for item in dict_items
                        ]
                    }
            
            fields_with_dict.append(field_dict)
        
        # 获取表关联关系（作为主表的关联）
        relations_list = []
        primary_relations = db.query(TableRelation).filter(
            TableRelation.primary_table_id == table_id,
            TableRelation.status == True
        ).all()
        
        for relation in primary_relations:
            # 获取关联的表和字段名称
            foreign_table = db.query(DataTable).filter(DataTable.id == relation.foreign_table_id).first()
            primary_field = db.query(TableField).filter(TableField.id == relation.primary_field_id).first()
            foreign_field = db.query(TableField).filter(TableField.id == relation.foreign_field_id).first()
            
            if foreign_table and primary_field and foreign_field:
                relations_list.append({
                    "id": relation.id,
                    "relation_name": relation.relation_name,
                    "primary_table_id": relation.primary_table_id,
                    "primary_table_name": table.table_name,
                    "primary_field_id": relation.primary_field_id,
                    "primary_field_name": primary_field.field_name,
                    "foreign_table_id": relation.foreign_table_id,
                    "foreign_table_name": foreign_table.table_name,
                    "foreign_field_id": relation.foreign_field_id,
                    "foreign_field_name": foreign_field.field_name,
                    "join_type": relation.join_type,
                    "description": relation.description,
                    "status": relation.status
                })
        
        # 也获取作为外键表的关联
        foreign_relations = db.query(TableRelation).filter(
            TableRelation.foreign_table_id == table_id,
            TableRelation.status == True
        ).all()
        
        for relation in foreign_relations:
            # 获取关联的表和字段名称
            primary_table = db.query(DataTable).filter(DataTable.id == relation.primary_table_id).first()
            primary_field = db.query(TableField).filter(TableField.id == relation.primary_field_id).first()
            foreign_field = db.query(TableField).filter(TableField.id == relation.foreign_field_id).first()
            
            if primary_table and primary_field and foreign_field:
                relations_list.append({
                    "id": relation.id,
                    "relation_name": relation.relation_name,
                    "primary_table_id": relation.primary_table_id,
                    "primary_table_name": primary_table.table_name,
                    "primary_field_id": relation.primary_field_id,
                    "primary_field_name": primary_field.field_name,
                    "foreign_table_id": relation.foreign_table_id,
                    "foreign_table_name": table.table_name,
                    "foreign_field_id": relation.foreign_field_id,
                    "foreign_field_name": foreign_field.field_name,
                    "join_type": relation.join_type,
                    "description": relation.description,
                    "status": relation.status
                })
        
        # 构建完整响应
        table_detail = {
            "id": table.id,
            "data_source_id": table.data_source_id,
            "table_name": table.table_name,
            "display_name": table.display_name,
            "description": table.description,
            "data_mode": table.data_mode,
            "status": table.status,
            "field_count": table.field_count,
            "row_count": table.row_count,
            "fields": fields_with_dict,
            "relations": relations_list,
            "created_by": table.created_by,
            "created_at": table.created_at,
            "updated_at": table.updated_at
        }
        
        logger.info(f"Retrieved detailed information for table {table_id}: {len(fields_with_dict)} fields, {len(relations_list)} relations")
        return DataTableDetailResponse(**table_detail)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve detailed data table information for {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据表详情失败")


@router.put("/{table_id}", response_model=DataTableResponse)
async def update_data_table(
    table_id: str,
    table_data: DataTableUpdate,
    db: Session = Depends(get_db)
):
    """
    更新数据表
    
    - 支持部分更新
    - 验证数据完整性
    - 验证数据源是否存在
    """
    logger.info(f"Updating data table {table_id}")
    
    try:
        # 获取现有数据表
        existing_table = data_table_service.get_table_by_id(db, table_id)
        
        if not existing_table:
            logger.warning(f"Data table with ID {table_id} not found for update")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 如果更新了数据源ID，验证新数据源是否存在
        if table_data.source_id and table_data.source_id != existing_table.data_source_id:
            source = db.query(DataSource).filter(DataSource.id == table_data.source_id).first()
            if not source:
                logger.warning(f"Data source with ID {table_data.source_id} not found for update")
                raise HTTPException(
                    status_code=404, 
                    detail=f"数据源不存在: {table_data.source_id}"
                )
            
            # 验证新数据源下是否已存在同名表
            existing_table_in_new_source = data_table_service.get_table_by_name_and_source(db, existing_table.table_name, table_data.source_id)
            if existing_table_in_new_source:
                logger.warning(f"Data table with name {existing_table.table_name} already exists in source {table_data.source_id}")
                raise HTTPException(
                    status_code=409, 
                    detail=f"数据源 {table_data.source_id} 下已存在同名表: {existing_table.table_name}"
                )
        
        # 更新数据表
        db_table = data_table_service.update_table(db, table_id, table_data)
        
        # 转换为响应模型
        table_dict = db_table.to_dict()
        logger.info(f"Data table {table_id} updated successfully")
        return DataTableResponse(**table_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error updating data table: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        # 服务层抛出的业务逻辑错误
        logger.error(f"Business logic error updating data table: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update data table {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新数据表失败")


@router.delete("/{table_id}", status_code=204)
async def delete_data_table(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    删除数据表
    
    - 检查是否有关联关系
    - 有关联时返回错误提示
    """
    logger.info(f"Attempting to delete data table with ID: {table_id}")
    
    try:
        # 检查是否有关联关系（删除关系后方可删除表）
        has_related_relations = data_table_service.has_related_relations(db, table_id)

        if has_related_relations:
            logger.warning(f"Cannot delete data table {table_id}: has related relations")
            raise HTTPException(
                status_code=400, 
                detail="该数据表仍有关联关系，无法删除。请先删除与该表相关的表关联记录。"
            )
        
        # 删除数据表
        success = data_table_service.delete_table(db, table_id)
        
        if not success:
            logger.warning(f"Data table with ID {table_id} not found for deletion")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        logger.info(f"Data table {table_id} deleted successfully")

    except HTTPException:
        # 透传业务错误，避免被包装成500
        raise
    except Exception as e:
        logger.error(f"Failed to delete data table {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除数据表失败")


# 新增：获取数据表的所有字段
@router.get("/{table_id}/columns", response_model=List[dict])
async def get_data_table_columns(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    获取数据表的所有字段
    
    返回字段列表，包含字段名、数据类型、是否为主键等信息
    """
    logger.info(f"Retrieving columns for data table ID: {table_id}")
    
    try:
        # 获取数据表
        table = data_table_service.get_table_by_id(db, table_id)
        
        if not table:
            logger.warning(f"Data table with ID {table_id} not found")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 获取字段列表
        columns = data_table_service.get_table_columns(db, table_id)
        
        # 转换为字典格式
        column_list = [column.to_dict() for column in columns]
        
        logger.info(f"Successfully retrieved {len(column_list)} columns for data table {table_id}")
        return column_list
        
    except Exception as e:
        logger.error(f"Failed to retrieve columns for data table {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取字段列表失败")


# 新增：刷新数据表信息（从数据库中重新获取表结构）
@router.post("/{table_id}/refresh", response_model=DataTableResponse)
async def refresh_data_table(
    table_id: str,
    db: Session = Depends(get_db)
):
    """
    刷新数据表信息
    
    从数据源数据库中重新获取表结构信息，更新row_count、column_count等信息
    
    注意：此功能需要连接到数据源数据库，需要在服务层实现具体逻辑
    """
    logger.info(f"Refreshing data table information for ID: {table_id}")
    
    try:
        # 获取数据表
        table = data_table_service.get_table_by_id(db, table_id)
        
        if not table:
            logger.warning(f"Data table with ID {table_id} not found")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 这里需要调用表发现服务来获取最新的表结构信息
        # 由于表发现服务依赖于数据源配置，我们需要从数据库中获取数据源信息
        source = db.query(DataSource).filter(DataSource.id == table.source_id).first()
        
        if not source:
            logger.warning(f"Data source with ID {table.source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 在实际实现中，这里应该调用TableDiscoveryService来获取最新的表结构信息
        # 由于我们还没有实现这个功能，暂时只更新last_refreshed时间
        from datetime import datetime
        table.last_refreshed = datetime.now()
        db.commit()
        db.refresh(table)
        
        # 转换为响应模型
        table_dict = table.to_dict()
        logger.info(f"Data table {table_id} refreshed successfully")
        return DataTableResponse(**table_dict)
        
    except Exception as e:
        logger.error(f"Failed to refresh data table {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="刷新数据表信息失败")


# 新增：同步表结构 - 异步版本
@router.post("/{table_id}/sync", response_model=dict)
async def sync_table_structure(
    table_id: str,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    异步同步数据表结构
    
    从数据源数据库读取表结构，自动创建/更新table_fields记录
    立即返回任务ID，后台执行同步操作
    
    支持MySQL和PostgreSQL数据库
    处理连接错误和权限错误
    """
    logger.info(f"Syncing table structure for ID: {table_id}")
    
    try:
        # 验证数据表是否存在
        table = db.query(DataTable).filter(DataTable.id == table_id).first()
        if not table:
            logger.warning(f"Data table with ID {table_id} not found")
            raise HTTPException(status_code=404, detail="数据表不存在")
        
        # 创建异步任务
        task_id = task_manager.create_task(table_id)
        
        # 将异步任务添加到后台任务中
        if background_tasks:
            background_tasks.add_task(async_table_sync_task, task_id, table_id)
        
        logger.info(f"Created async sync task {task_id} for table {table_id}")
        return {"task_id": task_id, "message": "表结构同步任务已启动，将在后台执行"}
        
    except Exception as e:
        logger.error(f"Failed to start async sync task for {table_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="启动同步任务失败")


# 新增：查询表结构同步任务状态
@router.get("/{table_id}/sync/status", response_model=dict)
async def get_sync_task_status(
    table_id: str,
    task_id: str
):
    """
    查询表结构同步任务状态
    
    Args:
        table_id: 数据表ID
        task_id: 同步任务ID
        
    Returns:
        dict: 任务状态信息
    """
    logger.info(f"Checking sync task status for table {table_id}, task {task_id}")
    
    # 验证数据表是否存在
    db = next(get_db())
    table = db.query(DataTable).filter(DataTable.id == table_id).first()
    if not table:
        logger.warning(f"Data table with ID {table_id} not found")
        raise HTTPException(status_code=404, detail="数据表不存在")
    
    # 获取任务状态
    task = task_manager.get_task(task_id)
    if not task:
        logger.warning(f"Sync task {task_id} not found")
        raise HTTPException(status_code=404, detail="同步任务不存在")
    
    # 验证任务是否属于该数据表
    if task["table_id"] != table_id:
        logger.warning(f"Task {task_id} does not belong to table {table_id}")
        raise HTTPException(status_code=400, detail="任务ID与数据表不匹配")
    
    # 返回任务状态
    result = {
        "task_id": task_id,
        "table_id": table_id,
        "status": task["status"],
        "progress": task["progress"],
        "started_at": task["started_at"].isoformat() if task["started_at"] else None,
        "ended_at": task["ended_at"].isoformat() if task["ended_at"] else None,
        "result": task["result"],
        "error": task["error"]
    }
    
    logger.info(f"Sync task {task_id} status: {task["status"]}, progress: {task["progress"]}%")
    return result


# 新增：取消表结构同步任务
@router.post("/{table_id}/sync/cancel", response_model=dict)
async def cancel_sync_task(
    table_id: str,
    task_id: str
):
    """
    取消表结构同步任务
    
    Args:
        table_id: 数据表ID
        task_id: 同步任务ID
        
    Returns:
        dict: 取消结果
    """
    logger.info(f"Cancelling sync task {task_id} for table {table_id}")
    
    # 验证数据表是否存在
    db = next(get_db())
    table = db.query(DataTable).filter(DataTable.id == table_id).first()
    if not table:
        logger.warning(f"Data table with ID {table_id} not found")
        raise HTTPException(status_code=404, detail="数据表不存在")
    
    # 获取任务状态
    task = task_manager.get_task(task_id)
    if not task:
        logger.warning(f"Sync task {task_id} not found")
        raise HTTPException(status_code=404, detail="同步任务不存在")
    
    # 验证任务是否属于该数据表
    if task["table_id"] != table_id:
        logger.warning(f"Task {task_id} does not belong to table {table_id}")
        raise HTTPException(status_code=400, detail="任务ID与数据表不匹配")
    
    # 检查任务是否已经完成或取消
    if task["status"] in [SyncTaskStatus.COMPLETED, SyncTaskStatus.FAILED, SyncTaskStatus.CANCELLED]:
        logger.info(f"Task {task_id} is already in terminal state: {task["status"]}")
        return {"task_id": task_id, "status": "已取消", "message": "任务已处于完成或取消状态"}
    
    # 取消任务
    task_manager.cancel_task(task_id)
    
    logger.info(f"Sync task {task_id} cancelled successfully")
    return {"task_id": task_id, "status": "cancelled", "message": "同步任务已取消"}


# 新增：表发现API - 从数据源发现所有表
@router.get("/discover/{source_id}", response_model=List[dict])
async def discover_tables_from_source(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    从数据源发现所有表
    
    Args:
        source_id: 数据源ID
        
    Returns:
        List[dict]: 发现的表列表，包含表名、注释、行数等信息
    """
    logger.info(f"Discovering tables from data source: {source_id}")
    
    try:
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 发现表
        tables = table_discovery_service.discover_tables(data_source)
        
        logger.info(f"Successfully discovered {len(tables)} tables from data source {source_id}")
        return tables
        
    except Exception as e:
        logger.error(f"Failed to discover tables from data source {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="表发现失败")


# 新增：同步单个表结构
@router.post("/sync-structure", response_model=DataTableResponse)
async def sync_single_table_structure(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    同步单个表的结构
    
    Args:
        request: 包含source_id和table_name的请求体
        
    Returns:
        DataTableResponse: 同步后的数据表信息
    """
    source_id = request.get('source_id')
    table_name = request.get('table_name')
    
    if not source_id or not table_name:
        raise HTTPException(status_code=400, detail="缺少必要参数: source_id 和 table_name")
    
    logger.info(f"Syncing table structure for {table_name} from data source {source_id}")
    
    try:
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 同步表结构
        synced_table = table_discovery_service.sync_table_structure(db, data_source, table_name)
        
        # 转换为响应模型
        table_dict = synced_table.to_dict()
        logger.info(f"Successfully synced table structure for {table_name}")
        return DataTableResponse(**table_dict)
        
    except Exception as e:
        logger.error(f"Failed to sync table structure for {table_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="表结构同步失败")


# 新增：批量同步表结构
@router.post("/batch-sync-structure", response_model=dict)
async def batch_sync_table_structures(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    批量同步多个表的结构
    
    Args:
        request: 包含source_id和table_names的请求体
        
    Returns:
        dict: 同步结果统计
    """
    source_id = request.get('source_id')
    table_names = request.get('table_names', [])
    
    if not source_id or not table_names:
        raise HTTPException(status_code=400, detail="缺少必要参数: source_id 和 table_names")
    
    logger.info(f"Batch syncing {len(table_names)} tables from data source {source_id}")
    
    try:
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 批量同步表结构
        synced_tables = table_discovery_service.batch_sync_tables(db, data_source, table_names)
        
        result = {
            "total_requested": len(table_names),
            "successfully_synced": len(synced_tables),
            "failed_count": len(table_names) - len(synced_tables),
            "synced_tables": [table.table_name for table in synced_tables]
        }
        
        logger.info(f"Batch sync completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to batch sync table structures: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="批量表结构同步失败")


# 新增：获取表结构详情（不同步，仅查询）
@router.get("/structure/{source_id}/{table_name}", response_model=dict)
async def get_table_structure_from_source(
    source_id: str,
    table_name: str,
    db: Session = Depends(get_db)
):
    """
    从数据源获取表结构详情（不同步到本地）
    
    Args:
        source_id: 数据源ID
        table_name: 表名
        
    Returns:
        dict: 表结构信息，包含字段列表
    """
    logger.info(f"Getting table structure for {table_name} from data source {source_id}")
    
    try:
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 获取表结构
        table_structure = table_discovery_service.get_table_structure(data_source, table_name)
        
        logger.info(f"Successfully retrieved table structure for {table_name}")
        return table_structure
        
    except Exception as e:
        logger.error(f"Failed to get table structure for {table_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取表结构失败")


# 新增：测试数据源连接
@router.post("/test-connection/{source_id}", response_model=dict)
async def test_data_source_connection(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    测试数据源连接
    
    Args:
        source_id: 数据源ID
        
    Returns:
        dict: 连接测试结果
    """
    logger.info(f"Testing connection for data source: {source_id}")
    
    try:
        # 获取数据源
        data_source = db.query(DataSource).filter(DataSource.id == source_id).first()
        if not data_source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 测试连接
        success, message = table_discovery_service.test_connection(data_source)
        
        result = {
            "success": success,
            "message": message,
            "source_id": source_id,
            "source_name": data_source.name
        }
        
        logger.info(f"Connection test result for {source_id}: {success}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to test connection for data source {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="连接测试失败")