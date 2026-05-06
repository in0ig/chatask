from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.utils import get_db_session
from src.models.knowledge_item_model import KnowledgeItem
from src.models.knowledge_base_model import KnowledgeBase
from src.schemas.knowledge_item_schema import (
    KnowledgeItemCreate,
    KnowledgeItemUpdate,
    KnowledgeItemResponse,
    KnowledgeItemListResponse
)

router = APIRouter(tags=["knowledge-items"])

@router.post("/", response_model=KnowledgeItemResponse)
async def create_knowledge_item(
    item_data: KnowledgeItemCreate,
    db: Session = Depends(get_db_session)
):
    """创建知识项"""
    
    # 验证知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == item_data.knowledge_base_id
    ).first()
    
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    # 根据类型验证必需字段
    if item_data.type == "TERM" and not item_data.name:
        raise HTTPException(status_code=400, detail="名词知识必须提供知识名称")
    
    if item_data.type == "EVENT" and not item_data.event_date_start:
        raise HTTPException(status_code=400, detail="事件知识必须提供事件开始时间")
    
    # 创建知识项
    db_item = KnowledgeItem(
        knowledge_base_id=item_data.knowledge_base_id,
        type=item_data.type,
        name=item_data.name,
        explanation=item_data.explanation,
        example_question=item_data.example_question,
        event_date_start=item_data.event_date_start,
        event_date_end=item_data.event_date_end
    )
    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return KnowledgeItemResponse.from_orm(db_item)

@router.get("/", response_model=KnowledgeItemListResponse)
async def get_knowledge_items(
    knowledge_base_id: Optional[str] = Query(None, description="知识库ID"),
    type: Optional[str] = Query(None, description="知识类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db_session)
):
    """获取知识项列表"""
    
    query = db.query(KnowledgeItem)
    
    # 按知识库筛选
    if knowledge_base_id:
        query = query.filter(KnowledgeItem.knowledge_base_id == knowledge_base_id)
    
    # 按类型筛选
    if type:
        query = query.filter(KnowledgeItem.type == type)
    
    # 计算总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    return KnowledgeItemListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

@router.get("/{item_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    item_id: str,
    db: Session = Depends(get_db_session)
):
    """获取单个知识项"""
    
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="知识项不存在")
    
    return KnowledgeItemResponse.from_orm(item)

@router.put("/{item_id}", response_model=KnowledgeItemResponse)
async def update_knowledge_item(
    item_id: str,
    item_data: KnowledgeItemUpdate,
    db: Session = Depends(get_db_session)
):
    """更新知识项"""
    
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="知识项不存在")
    
    # 更新字段
    update_data = item_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    
    item.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(item)
    
    return KnowledgeItemResponse.from_orm(item)

@router.delete("/{item_id}")
async def delete_knowledge_item(
    item_id: str,
    db: Session = Depends(get_db_session)
):
    """删除知识项"""
    
    item = db.query(KnowledgeItem).filter(KnowledgeItem.id == item_id).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="知识项不存在")
    
    db.delete(item)
    db.commit()
    
    return {"message": "知识项删除成功"}

@router.get("/knowledge-base/{knowledge_base_id}/items", response_model=List[KnowledgeItemResponse])
async def get_items_by_knowledge_base(
    knowledge_base_id: str,
    db: Session = Depends(get_db_session)
):
    """获取指定知识库的所有知识项"""
    
    # 验证知识库是否存在
    knowledge_base = db.query(KnowledgeBase).filter(
        KnowledgeBase.id == knowledge_base_id
    ).first()
    
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")
    
    items = db.query(KnowledgeItem).filter(
        KnowledgeItem.knowledge_base_id == knowledge_base_id
    ).order_by(KnowledgeItem.created_at.desc()).all()
    
    return [KnowledgeItemResponse.from_orm(item) for item in items]