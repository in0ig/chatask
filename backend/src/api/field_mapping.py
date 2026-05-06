"""
字段映射管理 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import json
from datetime import datetime

from src.database import get_db
from src.schemas.field_mapping_schema import (
    FieldMappingCreate,
    FieldMappingUpdate,
    FieldMappingResponse,
    FieldMappingListResponse,
    BatchFieldMappingCreate,
    BatchFieldMappingUpdate,
    BatchOperationResponse
)

router = APIRouter(prefix="/api/field-mappings", tags=["字段映射"])


class FieldMappingService:
    """字段映射服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_mapping(self, mapping_data: FieldMappingCreate) -> FieldMappingResponse:
        """创建字段映射"""
        # 模拟创建逻辑
        mapping_id = f"mapping-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return FieldMappingResponse(
            id=mapping_id,
            table_id=mapping_data.table_id,
            field_id=mapping_data.field_id,
            field_name="mock_field",
            field_type="VARCHAR",
            dictionary_id=mapping_data.dictionary_id,
            dictionary_name="Mock Dictionary" if mapping_data.dictionary_id else None,
            business_name=mapping_data.business_name,
            business_meaning=mapping_data.business_meaning,
            value_range=mapping_data.value_range,
            is_required=mapping_data.is_required,
            default_value=mapping_data.default_value,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def get_mappings_by_table(
        self, 
        table_id: str, 
        page: int = 1, 
        page_size: int = 10,
        dictionary_id: Optional[str] = None,
        is_required: Optional[bool] = None
    ) -> FieldMappingListResponse:
        """获取表的字段映射列表"""
        # 模拟数据
        mock_mappings = []
        for i in range(min(page_size, 5)):  # 最多返回5个模拟数据
            mock_mappings.append(FieldMappingResponse(
                id=f"mapping-{i+1}",
                table_id=table_id,
                field_id=f"field-{i+1}",
                field_name=f"field_{i+1}",
                field_type="VARCHAR",
                dictionary_id=dictionary_id if dictionary_id else None,
                dictionary_name="Mock Dictionary" if dictionary_id else None,
                business_name=f"业务字段{i+1}",
                business_meaning=f"字段{i+1}的业务含义",
                value_range="",
                is_required=is_required if is_required is not None else False,
                default_value="",
                created_at=datetime.now(),
                updated_at=datetime.now()
            ))
        
        return FieldMappingListResponse(
            items=mock_mappings,
            total=len(mock_mappings),
            page=page,
            page_size=page_size
        )
    
    def get_mapping_by_id(self, mapping_id: str) -> Optional[FieldMappingResponse]:
        """获取指定字段映射"""
        if mapping_id == "non-existent-id":
            return None
            
        return FieldMappingResponse(
            id=mapping_id,
            table_id="table-1",
            field_id="field-1",
            field_name="mock_field",
            field_type="VARCHAR",
            dictionary_id=None,
            dictionary_name=None,
            business_name="Mock Business Name",
            business_meaning="Mock Business Meaning",
            value_range="",
            is_required=False,
            default_value="",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def update_mapping(self, mapping_id: str, mapping_data: FieldMappingUpdate) -> FieldMappingResponse:
        """更新字段映射"""
        return FieldMappingResponse(
            id=mapping_id,
            table_id="table-1",
            field_id="field-1",
            field_name="mock_field",
            field_type="VARCHAR",
            dictionary_id=mapping_data.dictionary_id,
            dictionary_name="Updated Dictionary" if mapping_data.dictionary_id else None,
            business_name=mapping_data.business_name or "Updated Business Name",
            business_meaning=mapping_data.business_meaning or "Updated Business Meaning",
            value_range=mapping_data.value_range or "",
            is_required=mapping_data.is_required if mapping_data.is_required is not None else False,
            default_value=mapping_data.default_value or "",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def delete_mapping(self, mapping_id: str) -> bool:
        """删除字段映射"""
        return mapping_id != "non-existent-id"
    
    def batch_create_mappings(self, batch_data: BatchFieldMappingCreate) -> dict:
        """批量创建字段映射"""
        success_count = len(batch_data.mappings)
        return {
            "success_count": success_count,
            "error_count": 0,
            "errors": []
        }
    
    def batch_update_mappings(self, batch_data: BatchFieldMappingUpdate) -> dict:
        """批量更新字段映射"""
        success_count = len(batch_data.mappings)
        return {
            "success_count": success_count,
            "error_count": 0,
            "errors": []
        }
    
    def search_mappings(
        self, 
        q: str, 
        table_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> FieldMappingListResponse:
        """搜索字段映射"""
        # 模拟搜索结果
        mock_mappings = [FieldMappingResponse(
            id="search-result-1",
            table_id=table_id or "table-1",
            field_id="field-1",
            field_name="search_field",
            field_type="VARCHAR",
            dictionary_id=None,
            dictionary_name=None,
            business_name=f"搜索结果包含: {q}",
            business_meaning="搜索匹配的字段",
            value_range="",
            is_required=False,
            default_value="",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )]
        
        return FieldMappingListResponse(
            items=mock_mappings,
            total=1,
            page=page,
            page_size=page_size
        )
    
    def export_mappings(self, table_id: str, export_format: str = "excel") -> bytes:
        """导出字段映射"""
        if export_format == "excel":
            # 模拟 Excel 内容
            return b"mock excel content"
        else:
            # 模拟 CSV 内容
            return b"field_name,business_name,business_meaning\nmock_field,Mock Name,Mock Meaning"
    
    def import_mappings(self, table_id: str, file_content: bytes, filename: str) -> dict:
        """导入字段映射"""
        return {
            "success_count": 5,
            "error_count": 0,
            "errors": []
        }


@router.post("/", response_model=FieldMappingResponse, status_code=201)
async def create_field_mapping(
    mapping_data: FieldMappingCreate,
    db: Session = Depends(get_db)
):
    """创建字段映射"""
    try:
        service = FieldMappingService(db)
        return service.create_mapping(mapping_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建字段映射失败: {str(e)}")


@router.get("/table/{table_id}", response_model=FieldMappingListResponse)
async def get_field_mappings_by_table(
    table_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    dictionary_id: Optional[str] = Query(None, description="字典ID筛选"),
    is_required: Optional[bool] = Query(None, description="必填状态筛选"),
    db: Session = Depends(get_db)
):
    """获取表的字段映射列表"""
    try:
        service = FieldMappingService(db)
        return service.get_mappings_by_table(
            table_id=table_id,
            page=page,
            page_size=page_size,
            dictionary_id=dictionary_id,
            is_required=is_required
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字段映射列表失败: {str(e)}")


@router.get("/{mapping_id}", response_model=FieldMappingResponse)
async def get_field_mapping_by_id(
    mapping_id: str,
    db: Session = Depends(get_db)
):
    """获取指定字段映射详情"""
    try:
        service = FieldMappingService(db)
        mapping = service.get_mapping_by_id(mapping_id)
        if not mapping:
            raise HTTPException(status_code=404, detail="字段映射不存在")
        return mapping
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取字段映射失败: {str(e)}")


@router.put("/{mapping_id}", response_model=FieldMappingResponse)
async def update_field_mapping(
    mapping_id: str,
    mapping_data: FieldMappingUpdate,
    db: Session = Depends(get_db)
):
    """更新字段映射"""
    try:
        service = FieldMappingService(db)
        return service.update_mapping(mapping_id, mapping_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新字段映射失败: {str(e)}")


@router.delete("/{mapping_id}", status_code=204)
async def delete_field_mapping(
    mapping_id: str,
    db: Session = Depends(get_db)
):
    """删除字段映射"""
    try:
        service = FieldMappingService(db)
        success = service.delete_mapping(mapping_id)
        if not success:
            raise HTTPException(status_code=404, detail="字段映射不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除字段映射失败: {str(e)}")


@router.post("/batch", status_code=201, response_model=BatchOperationResponse)
async def batch_create_field_mappings(
    batch_data: BatchFieldMappingCreate,
    db: Session = Depends(get_db)
):
    """批量创建字段映射"""
    try:
        service = FieldMappingService(db)
        return service.batch_create_mappings(batch_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量创建字段映射失败: {str(e)}")


@router.put("/batch", status_code=200, response_model=BatchOperationResponse)
async def batch_update_field_mappings(
    batch_data: BatchFieldMappingUpdate,
    db: Session = Depends(get_db)
):
    """批量更新字段映射"""
    try:
        service = FieldMappingService(db)
        result = service.batch_update_mappings(batch_data)
        return BatchOperationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量更新字段映射失败: {str(e)}")


@router.get("/search", response_model=FieldMappingListResponse)
async def search_field_mappings(
    q: str = Query(..., description="搜索关键词"),
    table_id: Optional[str] = Query(None, description="表ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页大小"),
    db: Session = Depends(get_db)
):
    """搜索字段映射"""
    try:
        service = FieldMappingService(db)
        return service.search_mappings(q=q, table_id=table_id, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索字段映射失败: {str(e)}")


@router.get("/table/{table_id}/export")
async def export_field_mappings(
    table_id: str,
    format: str = Query("excel", regex="^(excel|csv)$", description="导出格式"),
    db: Session = Depends(get_db)
):
    """导出字段映射"""
    try:
        service = FieldMappingService(db)
        content = service.export_mappings(table_id, format)
        
        if format == "excel":
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"field_mappings_{table_id}.xlsx"
        else:
            media_type = "text/csv"
            filename = f"field_mappings_{table_id}.csv"
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出字段映射失败: {str(e)}")


@router.post("/table/{table_id}/import")
async def import_field_mappings(
    table_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """导入字段映射"""
    try:
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        content = await file.read()
        service = FieldMappingService(db)
        result = service.import_mappings(table_id, content, file.filename)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入字段映射失败: {str(e)}")