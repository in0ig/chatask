from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.knowledge_base_model import KnowledgeBase
from src.utils import get_db_session
from src.schemas.knowledge_base_schema import KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseResponse

router = APIRouter(tags=["knowledge-bases"])

@router.get("/", response_model=List[KnowledgeBaseResponse])
def get_knowledge_bases(
    type: Optional[str] = None,
    scope: Optional[str] = None,
    status: Optional[bool] = None,
    db: Session = Depends(get_db_session)
):
    """获取知识库列表，支持按类型、范围和状态筛选"""
    query = db.query(KnowledgeBase)
    
    if type:
        query = query.filter(KnowledgeBase.type == type)
    if scope:
        query = query.filter(KnowledgeBase.scope == scope)
    if status is not None:
        query = query.filter(KnowledgeBase.status == status)
    
    knowledge_bases = query.all()
    return [KnowledgeBaseResponse.from_orm(kb) for kb in knowledge_bases]

@router.post("/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db_session)
):
    """创建新的知识库"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Received knowledge base creation request: {knowledge_base.dict()}")
        
        # 检查名称是否已存在
        existing = db.query(KnowledgeBase).filter(KnowledgeBase.name == knowledge_base.name).first()
        if existing:
            logger.warning(f"Knowledge base name already exists: {knowledge_base.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="知识库名称已存在"
            )
        
        # 创建新的知识库实例
        db_knowledge_base = KnowledgeBase(**knowledge_base.dict())
        db.add(db_knowledge_base)
        db.commit()
        db.refresh(db_knowledge_base)
        
        logger.info(f"Knowledge base created successfully: {db_knowledge_base.id}")
        return KnowledgeBaseResponse.from_orm(db_knowledge_base)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating knowledge base: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )

@router.put("/{id}", response_model=KnowledgeBaseResponse)
def update_knowledge_base(
    id: str,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db_session)
):
    """更新指定ID的知识库"""
    db_knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == id).first()
    
    if not db_knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    # 检查名称是否已存在（排除自身）
    if knowledge_base.name:
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.name == knowledge_base.name,
            KnowledgeBase.id != id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="知识库名称已存在"
            )
    
    # 更新字段
    for field, value in knowledge_base.dict(exclude_unset=True).items():
        setattr(db_knowledge_base, field, value)
    
    db_knowledge_base.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_knowledge_base)
    
    return KnowledgeBaseResponse.from_orm(db_knowledge_base)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    id: str,
    db: Session = Depends(get_db_session)
):
    """删除指定ID的知识库"""
    db_knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.id == id).first()
    
    if not db_knowledge_base:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="知识库未找到"
        )
    
    db.delete(db_knowledge_base)
    db.commit()
    
    return None