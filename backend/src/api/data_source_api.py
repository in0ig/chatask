import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pydantic import ValidationError
from sqlalchemy.orm import Session
from src.models.data_source_model import DataSource
from src.schemas.data_source_schema import (
    DataSourceCreate,
    DataSourceUpdate,
    DataSourceResponse,
    DataSourceListResponse,
    DatabaseType,
    AuthType,
    ConnectionStatus,
    DataSourceTestConnection
)
from src.services.data_source_service import DataSourceService
from src.utils.encryption import encrypt_password, decrypt_password
from src.database import get_db
from datetime import datetime
from src.services.table_discovery import TableDiscoveryService  # 导入表发现服务

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-sources", tags=["Data Sources"])

data_source_service = DataSourceService()

@router.get("/", response_model=DataSourceListResponse)
async def get_data_sources(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量，1-100"),
    search: Optional[str] = Query(None, description="搜索关键词（名称、描述）"),
    status: Optional[bool] = Query(None, description="启用状态：true/false"),
    db_type: Optional[DatabaseType] = Query(None, description="数据库类型：MySQL、SQL Server、PostgreSQL、ClickHouse"),
    source_type: Optional[str] = Query(None, description="数据源类型：DATABASE/FILE"),
    db: Session = Depends(get_db)
):
    """
    获取数据源列表
    
    支持分页、搜索、筛选功能
    密码字段已脱敏，不会返回
    """
    logger.info(f"Retrieving data sources with filters - page: {page}, page_size: {page_size}, search: {search}, status: {status}, db_type: {db_type}, source_type: {source_type}")
    
    try:
        sources, total = data_source_service.get_all_sources(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            db_type=db_type,
            source_type=source_type
        )
        
        # 转换为响应模型，自动脱敏密码
        response_sources = []
        for source in sources:
            # 创建响应对象，不包含密码
            source_dict = {
                'id': source.id,
                'name': source.name,
                'source_type': source.source_type,
                'db_type': source.db_type,
                'host': source.host,
                'port': source.port,
                'database_name': source.database_name,
                'auth_type': source.auth_type,
                'username': source.username,
                'domain': source.domain,
                'file_path': source.file_path,
                'connection_status': source.connection_status,
                'last_test_time': source.last_test_time.isoformat() if source.last_test_time else None,
                'description': source.description,
                'status': source.status,
                'created_by': source.created_by,
                'created_at': source.created_at.isoformat() if source.created_at else None,
                'updated_at': source.updated_at.isoformat() if source.updated_at else None
            }
            response_sources.append(DataSourceResponse(**source_dict))
        
        logger.info(f"Retrieved {len(sources)} data sources")
        return DataSourceListResponse(data=response_sources, total=total)
        
    except Exception as e:
        logger.error(f"Failed to retrieve data sources: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据源列表失败")


@router.post("/", response_model=DataSourceResponse, status_code=201)
async def create_data_source(
    source_data: DataSourceCreate,
    db: Session = Depends(get_db)
):
    """
    创建数据源
    
    - 验证必填字段
    - 密码自动加密存储
    - 支持所有数据库类型：MySQL、SQL Server
    - SQL Server 特殊验证：认证方式必填
    """
    logger.info(f"Creating new data source: {source_data.name}")
    
    try:
        # 验证SQL Server认证方式
        if source_data.db_type == DatabaseType.SQL_SERVER and not source_data.auth_type:
            raise HTTPException(
                status_code=400, 
                detail="当数据库类型为SQL Server时，认证方式为必填项"
            )
        
        # 验证密码长度
        if source_data.password and len(source_data.password) < 8:
            raise HTTPException(
                status_code=400, 
                detail="密码长度不能少于8位"
            )
        
        # 加密密码
        encrypted_password = None
        if source_data.password:
            try:
                encrypted_password = encrypt_password(source_data.password)
            except Exception as e:
                logger.error(f"Password encryption failed: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail="密码加密失败，请稍后重试"
                )
        
        # 创建数据源记录
        db_source = DataSource(
            name=source_data.name,
            source_type=source_data.source_type,
            db_type=source_data.db_type,
            host=source_data.host,
            port=source_data.port,
            database_name=source_data.database_name,
            auth_type=source_data.auth_type,
            username=source_data.username,
            password=encrypted_password,
            domain=source_data.domain,
            file_path=source_data.file_path,
            description=source_data.description,
            status=source_data.status,
            created_by=source_data.created_by
        )
        
        # 保存到数据库
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        
        # 转换为响应模型，自动脱敏密码
        source_dict = {
            'id': db_source.id,
            'name': db_source.name,
            'source_type': db_source.source_type,
            'db_type': db_source.db_type,
            'host': db_source.host,
            'port': db_source.port,
            'database_name': db_source.database_name,
            'auth_type': db_source.auth_type,
            'username': db_source.username,
            'domain': db_source.domain,
            'file_path': db_source.file_path,
            'connection_status': db_source.connection_status,
            'last_test_time': db_source.last_test_time.isoformat() if db_source.last_test_time else None,
            'description': db_source.description,
            'status': db_source.status,
            'created_by': db_source.created_by,
            'created_at': db_source.created_at.isoformat() if db_source.created_at else None,
            'updated_at': db_source.updated_at.isoformat() if db_source.updated_at else None
        }
        
        logger.info(f"Data source created successfully: {source_data.name} (ID: {db_source.id})")
        return DataSourceResponse(**source_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error creating data source: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create data source: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建数据源失败")


@router.get("/{source_id}", response_model=DataSourceResponse)
async def get_data_source_by_id(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    获取指定ID的数据源详情
    
    密码字段已脱敏，不会返回
    """
    logger.info(f"Retrieving data source details for ID: {source_id}")
    
    try:
        source = data_source_service.get_source_by_id(db, source_id)
        
        if not source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 转换为响应模型，自动脱敏密码
        source_dict = {
            'id': source.id,
            'name': source.name,
            'source_type': source.source_type,
            'db_type': source.db_type,
            'host': source.host,
            'port': source.port,
            'database_name': source.database_name,
            'auth_type': source.auth_type,
            'username': source.username,
            'domain': source.domain,
            'file_path': source.file_path,
            'connection_status': source.connection_status,
            'last_test_time': source.last_test_time.isoformat() if source.last_test_time else None,
            'description': source.description,
            'status': source.status,
            'created_by': source.created_by,
            'created_at': source.created_at.isoformat() if source.created_at else None,
            'updated_at': source.updated_at.isoformat() if source.updated_at else None
        }
        
        logger.info(f"Retrieved data source details for ID: {source_id}")
        return DataSourceResponse(**source_dict)
        
    except Exception as e:
        logger.error(f"Failed to retrieve data source {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取数据源详情失败")


@router.put("/{source_id}", response_model=DataSourceResponse)
async def update_data_source(
    source_id: str,
    source_data: DataSourceUpdate,
    db: Session = Depends(get_db)
):
    """
    更新数据源
    
    - 支持部分更新
    - 密码字段更新时自动加密
    - 验证数据完整性
    """
    logger.info(f"Updating data source {source_id}")
    
    try:
        # 获取现有数据源
        existing_source = data_source_service.get_source_by_id(db, source_id)
        
        if not existing_source:
            logger.warning(f"Data source with ID {source_id} not found for update")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 验证SQL Server认证方式
        if source_data.db_type == DatabaseType.SQL_SERVER and not source_data.auth_type:
            # 如果更新了数据库类型为SQL Server但未提供认证方式
            raise HTTPException(
                status_code=400, 
                detail="当数据库类型为SQL Server时，认证方式为必填项"
            )
        
        # 验证密码长度
        if source_data.password and len(source_data.password) < 8:
            raise HTTPException(
                status_code=400, 
                detail="密码长度不能少于8位"
            )
        
        # 加密密码（如果提供）
        encrypted_password = None
        if source_data.password:
            try:
                encrypted_password = encrypt_password(source_data.password)
            except Exception as e:
                logger.error(f"Password encryption failed: {str(e)}")
                raise HTTPException(
                    status_code=500, 
                    detail="密码加密失败，请稍后重试"
                )
        
        # 更新字段
        update_fields = {}
        for field, value in source_data.dict(exclude_unset=True).items():
            if field == 'password' and value:
                update_fields['password'] = encrypted_password
            elif field != 'password':
                update_fields[field] = value
        
        # 执行更新
        for field, value in update_fields.items():
            setattr(existing_source, field, value)
        
        db.commit()
        db.refresh(existing_source)
        
        # 转换为响应模型，自动脱敏密码
        source_dict = {
            'id': existing_source.id,
            'name': existing_source.name,
            'source_type': existing_source.source_type,
            'db_type': existing_source.db_type,
            'host': existing_source.host,
            'port': existing_source.port,
            'database_name': existing_source.database_name,
            'auth_type': existing_source.auth_type,
            'username': existing_source.username,
            'domain': existing_source.domain,
            'file_path': existing_source.file_path,
            'connection_status': existing_source.connection_status,
            'last_test_time': existing_source.last_test_time.isoformat() if existing_source.last_test_time else None,
            'description': existing_source.description,
            'status': existing_source.status,
            'created_by': existing_source.created_by,
            'created_at': existing_source.created_at.isoformat() if existing_source.created_at else None,
            'updated_at': existing_source.updated_at.isoformat() if existing_source.updated_at else None
        }
        
        logger.info(f"Data source {source_id} updated successfully")
        return DataSourceResponse(**source_dict)
        
    except ValidationError as e:
        logger.error(f"Validation error updating data source: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update data source {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="更新数据源失败")


@router.delete("/{source_id}", status_code=204)
async def delete_data_source(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    删除数据源
    
    - 检查是否有关联的数据表
    - 有关联时返回错误提示
    """
    logger.info(f"Attempting to delete data source with ID: {source_id}")
    
    try:
        # 检查是否有关联的数据表
        has_related_tables = data_source_service.has_related_tables(db, source_id)
        
        if has_related_tables:
            logger.warning(f"Cannot delete data source {source_id}: has related tables")
            raise HTTPException(
                status_code=400, 
                detail="该数据源有关联的数据表，无法删除。请先删除相关数据表。"
            )
        
        # 删除数据源
        success = data_source_service.delete_source(db, source_id)
        
        if not success:
            logger.warning(f"Data source with ID {source_id} not found for deletion")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        logger.info(f"Data source {source_id} deleted successfully")
        
    except Exception as e:
        logger.error(f"Failed to delete data source {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="删除数据源失败")


# 新增：数据源连接测试端点
@router.post("/test", response_model=dict)
async def test_data_source_connection(
    connection_data: DataSourceTestConnection,
    db: Session = Depends(get_db)
):
    """
    测试数据源连接
    
    支持 MySQL、SQL Server 连接测试
    返回连接延迟信息和友好错误提示
    
    参数说明：
    - 所有参数与创建数据源相同，但无需保存到数据库
    - 仅用于测试连接有效性
    
    返回格式：
    {
        "success": true/false,
        "message": "成功/失败信息",
        "latency_ms": int（连接延迟，毫秒，可选）
    }
    """
    logger.info(f"Testing connection for data source: {connection_data.name}")
    
    try:
        # 创建临时数据源对象用于测试
        temp_source = DataSource(
            id="test-temp",
            name=connection_data.name,
            source_type=connection_data.source_type,
            db_type=connection_data.db_type,
            host=connection_data.host,
            port=connection_data.port,
            database_name=connection_data.database_name,
            auth_type=connection_data.auth_type,
            username=connection_data.username,
            password=connection_data.password,
            domain=connection_data.domain,
            file_path=connection_data.file_path,
            description=connection_data.description,
            status=True,
            created_by=connection_data.created_by
        )
        
        # 使用连接测试服务进行测试
        from src.services.connection_test import ConnectionTestService
        result = ConnectionTestService.test_connection({
            "name": connection_data.name,
            "source_type": connection_data.source_type,
            "db_type": connection_data.db_type,
            "host": connection_data.host,
            "port": connection_data.port,
            "database_name": connection_data.database_name,
            "auth_type": connection_data.auth_type,
            "username": connection_data.username,
            "password": connection_data.password,
            "domain": connection_data.domain
        })

        logger.info(
            "Connection test result - name=%s, db_type=%s, host=%s, port=%s, success=%s, message=%s",
            connection_data.name,
            connection_data.db_type,
            connection_data.host,
            connection_data.port,
            result.success,
            result.message
        )
        
        # 返回符合要求的格式
        return {
            "success": result.success,
            "message": result.message,
            "latency_ms": result.latency_ms
        }
        
    except Exception as e:
        logger.error(f"Failed to test connection: {str(e)}", exc_info=True)
        
        # 返回友好的错误信息
        return {
            "success": False,
            "message": "连接测试失败，请检查配置信息",
            "latency_ms": None
        }


# 废弃的端点已移除，避免路由冲突

@router.post("/upload", include_in_schema=False)
async def upload_excel_deprecated():
    """
    [已废弃] 上传Excel文件
    
    请使用 /api/data-sources/ 端点创建数据源
    """
    return {"error": "此端点已废弃，请使用 /api/data-sources/ 端点创建数据源"}

@router.put("/{source_id}/activate", include_in_schema=False)
async def activate_data_source_deprecated():
    """
    [已废弃] 激活数据源
    
    请使用 /api/data-sources/{id} 端点更新数据源状态
    """
    return {"error": "此端点已废弃，请使用 /api/data-sources/{id} 端点更新数据源状态"}


# 新增：查询指定数据源的所有表列表
@router.get("/{source_id}/tables", response_model=dict)
async def get_data_source_tables(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    查询指定数据源的所有表列表
    
    支持 MySQL、SQL Server 两种数据库类型
    返回表名列表和基本信息（表名、表类型、注释等）
    
    参数：
    - source_id: 数据源ID（路径参数）
    
    返回格式：
    {
        "tables": [
            {
                "name": "table_name",
                "type": "TABLE",
                "comment": "注释"
            }
        ]
    }
    
    错误处理：
    - 数据源不存在：返回 404 错误
    - 连接失败：返回 500 错误和友好提示
    - 查询异常：返回 500 错误和友好提示
    """
    logger.info(f"Retrieving tables for data source ID: {source_id}")
    
    try:
        # 获取数据源信息
        source = data_source_service.get_source_by_id(db, source_id)
        
        if not source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 构建数据源配置字典
        data_source_config = {
            "name": source.name,
            "source_type": source.source_type,
            "db_type": source.db_type,
            "host": source.host,
            "port": source.port,
            "database_name": source.database_name,
            "username": source.username,
            "password": source.password,
            "domain": source.domain
        }
        
        # 使用表发现服务查询表列表
        result = TableDiscoveryService.discover_tables_by_data_source(data_source_config)
        
        if not result.success:
            logger.error(f"Table discovery failed for data source {source_id}: {result.error_message}")
            raise HTTPException(status_code=500, detail=result.error_message)
        
        logger.info(f"Successfully discovered {len(result.tables)} tables for data source {source_id}")
        return {"tables": [table.dict() for table in result.tables]}
        
    except HTTPException:
        # 重新抛出HTTP异常，保持原有错误处理
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to retrieve tables for data source {source_id}: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询表列表失败，请检查数据源配置和网络连接")


# 新增：连接池监控端点
@router.get("/{source_id}/pool/stats", response_model=dict)
async def get_connection_pool_stats(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    获取数据源连接池统计信息
    
    返回连接池的详细统计信息，包括连接数、状态、响应时间等
    
    参数：
    - source_id: 数据源ID（路径参数）
    
    返回格式：
    {
        "pool_id": "数据源ID",
        "db_type": "数据库类型",
        "total_connections": 总连接数,
        "active_connections": 活跃连接数,
        "idle_connections": 空闲连接数,
        "failed_connections": 失败连接数,
        "status": "连接池状态",
        "last_check_time": 最后检查时间,
        "average_response_time": 平均响应时间,
        "error_rate": 错误率
    }
    """
    logger.info(f"Getting connection pool stats for data source: {source_id}")
    
    try:
        # 检查数据源是否存在
        source = data_source_service.get_source_by_id(db, source_id)
        if not source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 获取连接池统计信息
        stats = data_source_service.get_connection_pool_stats(source_id)
        
        if not stats:
            logger.warning(f"Connection pool not found for data source {source_id}")
            raise HTTPException(status_code=404, detail="连接池不存在或未启用")
        
        logger.info(f"Retrieved connection pool stats for data source {source_id}")
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get connection pool stats for {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取连接池统计信息失败")


@router.post("/{source_id}/pool/health-check", response_model=dict)
async def check_connection_pool_health(
    source_id: str,
    db: Session = Depends(get_db)
):
    """
    检查数据源连接池健康状态
    
    执行连接池健康检查，验证连接是否正常工作
    
    参数：
    - source_id: 数据源ID（路径参数）
    
    返回格式：
    {
        "healthy": true/false,
        "message": "健康检查结果描述",
        "check_time": "检查时间戳"
    }
    """
    logger.info(f"Checking connection pool health for data source: {source_id}")
    
    try:
        # 检查数据源是否存在
        source = data_source_service.get_source_by_id(db, source_id)
        if not source:
            logger.warning(f"Data source with ID {source_id} not found")
            raise HTTPException(status_code=404, detail="数据源不存在")
        
        # 执行健康检查
        is_healthy = data_source_service.check_connection_pool_health(source_id)
        
        result = {
            "healthy": is_healthy,
            "message": "连接池健康" if is_healthy else "连接池异常",
            "check_time": datetime.now().isoformat()
        }
        
        logger.info(f"Connection pool health check completed for {source_id}: {is_healthy}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check connection pool health for {source_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="连接池健康检查失败")
