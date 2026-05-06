"""
ChatBI 兼容的数据源 API
为了兼容前端的 /api/datasources 路径请求
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from src.api.data_source_api import (
    get_data_sources as get_data_sources_impl,
    create_data_source as create_data_source_impl,
    get_data_source_by_id as get_data_source_by_id_impl,
    update_data_source as update_data_source_impl,
    delete_data_source as delete_data_source_impl,
    test_data_source_connection as test_data_source_connection_impl
)
from src.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    DatabaseType,
    DataSourceTestConnection
)
from src.database import get_db

# 创建日志记录器
logger = logging.getLogger(__name__)

# 创建兼容路由，使用 /api/datasources 前缀
router = APIRouter(prefix="/api/datasources", tags=["ChatBI Data Sources"])

@router.get("/", response_model=DataSourceListResponse)
async def get_datasources(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1-100"),
    search: Optional[str] = Query(None, description="搜索关键词（名称、描述）"),
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    db_type: Optional[DatabaseType] = Query(None, description="数据库类型：MySQL、SQL Server、PostgreSQL、ClickHouse"),
    source_type: Optional[str] = Query(None, description="数据源类型：DATABASE/FILE"),
    db: Session = Depends(get_db)
):
    """
    获取数据源列表 (ChatBI 兼容接口)
    
    兼容前端 /api/datasources 路径请求
    """
    logger.info("ChatBI datasources API: get_datasources called")
    return await get_data_sources_impl(page, page_size, search, status, db_type, source_type, db)

@router.post("/", response_model=DataSourceResponse, status_code=201)
async def create_datasource(
    source_data: DataSourceCreate,
    db: Session = Depends(get_db)
):
    """
    创建数据源 (ChatBI 兼容接口)
    """
    logger.info("ChatBI datasources API: create_datasource called")
    return await create_data_source_impl(source_data, db)

@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_datasource_by_id(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的数据源详情 (ChatBI 兼容接口)
    """
    logger.info("ChatBI datasources API: get_datasource_by_id called")
    return await get_data_source_by_id_impl(source_id, db)

@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_datasource(
    source_id: str,
    source_data: DataSourceUpdate,
    db: Session = Depends(get_db)
):
    """
    更新数据源 (ChatBI 兼容接口)
    """
    logger.info("ChatBI datasources API: update_datasource called")
    return await update_data_source_impl(source_id, source_data, db)

@router.delete("/{source_id}", status_code=204)
async def delete_datasource(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    删除数据源 (ChatBI 兼容接口)
    """
    logger.info("ChatBI datasources API: delete_datasource called")
    return await delete_data_source_impl(source_id, db)

@router.post("/test", response_model=dict)
async def test_datasource_connection(
    connection_data: DataSourceTestConnection,
    db: Session = Depends(get_db)
):
    """
    测试数据源连接 (ChatBI 兼容接口)
    """
    logger.info("ChatBI datasources API: test_datasource_connection called")
    return await test_data_source_connection_impl(connection_data, db)