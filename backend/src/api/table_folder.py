"""
表格文件夹管理 API
提供文件夹的 CRUD 操作和树形结构查询
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models.data_preparation_model import TableFolder, DataTable
from ..schemas.table_folder_schema import (
    TableFolderCreate,
    TableFolderUpdate,
    TableFolderResponse,
    TableFolderTree
)

router = APIRouter(prefix="/api/table-folders", tags=["表格文件夹管理"])


@router.get("/", response_model=List[TableFolderResponse])
async def get_folders(
    parent_id: Optional[str] = None,
    status: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取文件夹列表
    
    Args:
        parent_id: 父文件夹ID，为空时获取根文件夹
        status: 文件夹状态筛选
        db: 数据库会话
    
    Returns:
        文件夹列表
    """
    try:
        query = db.query(TableFolder)
        
        if parent_id is not None:
            query = query.filter(TableFolder.parent_id == parent_id)
        else:
            query = query.filter(TableFolder.parent_id.is_(None))
            
        if status is not None:
            query = query.filter(TableFolder.status == status)
            
        folders = query.order_by(TableFolder.sort_order, TableFolder.name).all()
        return folders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件夹列表失败: {str(e)}"
        )


@router.get("/tree", response_model=List[TableFolderTree])
async def get_folder_tree(
    status: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    获取文件夹树形结构
    
    Args:
        status: 文件夹状态筛选
        db: 数据库会话
    
    Returns:
        文件夹树形结构
    """
    try:
        # 获取所有文件夹
        query = db.query(TableFolder)
        if status is not None:
            query = query.filter(TableFolder.status == status)
        
        all_folders = query.order_by(TableFolder.sort_order, TableFolder.name).all()
        
        # 构建树形结构
        folder_dict = {folder.id: folder for folder in all_folders}
        tree = []
        
        for folder in all_folders:
            folder_data = TableFolderTree(
                id=folder.id,
                name=folder.name,
                description=folder.description,
                parent_id=folder.parent_id,
                sort_order=folder.sort_order or 0,
                status=folder.status or True,
                created_by=folder.created_by,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
                children=[]
            )
            
            if folder.parent_id is None:
                tree.append(folder_data)
            else:
                parent = folder_dict.get(folder.parent_id)
                if parent:
                    # 找到父节点在树中的位置并添加子节点
                    _add_child_to_tree(tree, folder.parent_id, folder_data)
        
        return tree
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取文件夹树形结构失败: {str(e)}"
        )


def _add_child_to_tree(tree: List[TableFolderTree], parent_id: str, child: TableFolderTree):
    """递归添加子节点到树形结构"""
    for node in tree:
        if node.id == parent_id:
            node.children.append(child)
            return True
        if _add_child_to_tree(node.children, parent_id, child):
            return True
    return False


@router.post("/", response_model=TableFolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: TableFolderCreate,
    db: Session = Depends(get_db)
):
    """
    创建文件夹
    
    Args:
        folder_data: 文件夹创建数据
        db: 数据库会话
    
    Returns:
        创建的文件夹信息
    """
    try:
        # 检查父文件夹是否存在
        if folder_data.parent_id:
            parent_folder = db.query(TableFolder).filter(
                TableFolder.id == folder_data.parent_id
            ).first()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="父文件夹不存在"
                )
        
        # 检查同级文件夹名称是否重复
        existing_folder = db.query(TableFolder).filter(
            TableFolder.name == folder_data.name,
            TableFolder.parent_id == folder_data.parent_id
        ).first()
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="同级目录下已存在相同名称的文件夹"
            )
        
        # 创建文件夹
        folder = TableFolder(**folder_data.dict())
        db.add(folder)
        db.commit()
        db.refresh(folder)
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建文件夹失败: {str(e)}"
        )


@router.get("/{folder_id}", response_model=TableFolderResponse)
async def get_folder(
    folder_id: str,
    db: Session = Depends(get_db)
):
    """
    获取文件夹详情
    
    Args:
        folder_id: 文件夹ID
        db: 数据库会话
    
    Returns:
        文件夹详情
    """
    try:
        folder = db.query(TableFolder).filter(TableFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件夹详情失败: {str(e)}"
        )


@router.put("/{folder_id}", response_model=TableFolderResponse)
async def update_folder(
    folder_id: str,
    folder_data: TableFolderUpdate,
    db: Session = Depends(get_db)
):
    """
    更新文件夹
    
    Args:
        folder_id: 文件夹ID
        folder_data: 文件夹更新数据
        db: 数据库会话
    
    Returns:
        更新后的文件夹信息
    """
    try:
        folder = db.query(TableFolder).filter(TableFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        # 检查父文件夹是否存在（如果要移动）
        if folder_data.parent_id and folder_data.parent_id != folder.parent_id:
            # 检查不能移动到自己的子文件夹
            if _is_descendant(db, folder_id, folder_data.parent_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能将文件夹移动到其子文件夹中"
                )
            
            parent_folder = db.query(TableFolder).filter(
                TableFolder.id == folder_data.parent_id
            ).first()
            if not parent_folder:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="目标父文件夹不存在"
                )
        
        # 检查同级文件夹名称是否重复（如果修改了名称或父文件夹）
        if (folder_data.name and folder_data.name != folder.name) or \
           (folder_data.parent_id and folder_data.parent_id != folder.parent_id):
            existing_folder = db.query(TableFolder).filter(
                TableFolder.name == (folder_data.name or folder.name),
                TableFolder.parent_id == (folder_data.parent_id or folder.parent_id),
                TableFolder.id != folder_id
            ).first()
            if existing_folder:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="同级目录下已存在相同名称的文件夹"
                )
        
        # 更新文件夹
        update_data = folder_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(folder, field, value)
        
        db.commit()
        db.refresh(folder)
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新文件夹失败: {str(e)}"
        )


def _is_descendant(db: Session, ancestor_id: str, descendant_id: str) -> bool:
    """检查是否为子孙文件夹关系"""
    current_id = descendant_id
    while current_id:
        if current_id == ancestor_id:
            return True
        folder = db.query(TableFolder).filter(TableFolder.id == current_id).first()
        if not folder:
            break
        current_id = folder.parent_id
    return False


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db)
):
    """
    删除文件夹
    
    Args:
        folder_id: 文件夹ID
        db: 数据库会话
    """
    try:
        folder = db.query(TableFolder).filter(TableFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        # 检查是否有子文件夹
        child_folders = db.query(TableFolder).filter(
            TableFolder.parent_id == folder_id
        ).count()
        if child_folders > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件夹下存在子文件夹，无法删除"
            )
        
        # 检查是否有数据表
        tables_count = db.query(DataTable).filter(
            DataTable.folder_id == folder_id
        ).count()
        if tables_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件夹下存在数据表，无法删除"
            )
        
        # 删除文件夹
        db.delete(folder)
        db.commit()
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文件夹失败: {str(e)}"
        )


@router.post("/{folder_id}/move", response_model=TableFolderResponse)
async def move_folder(
    folder_id: str,
    target_parent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    移动文件夹到指定父文件夹
    
    Args:
        folder_id: 要移动的文件夹ID
        target_parent_id: 目标父文件夹ID，为空表示移动到根目录
        db: 数据库会话
    
    Returns:
        移动后的文件夹信息
    """
    try:
        folder = db.query(TableFolder).filter(TableFolder.id == folder_id).first()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
        
        # 检查目标父文件夹是否存在
        if target_parent_id:
            # 检查不能移动到自己的子文件夹
            if _is_descendant(db, folder_id, target_parent_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能将文件夹移动到其子文件夹中"
                )
            
            target_parent = db.query(TableFolder).filter(
                TableFolder.id == target_parent_id
            ).first()
            if not target_parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="目标父文件夹不存在"
                )
        
        # 检查目标位置是否已有同名文件夹
        existing_folder = db.query(TableFolder).filter(
            TableFolder.name == folder.name,
            TableFolder.parent_id == target_parent_id,
            TableFolder.id != folder_id
        ).first()
        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="目标位置已存在相同名称的文件夹"
            )
        
        # 移动文件夹
        folder.parent_id = target_parent_id
        db.commit()
        db.refresh(folder)
        
        return folder
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移动文件夹失败: {str(e)}"
        )