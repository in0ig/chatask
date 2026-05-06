"""
数据准备服务层
实现数据表、字典、字典项等业务逻辑
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.models.data_preparation_model import Dictionary, DictionaryItem, DataTable, TableField, DynamicDictionaryConfig
from src.schemas.data_preparation_schema import (
    DictionaryCreate,
    DictionaryUpdate,
    DictionaryResponse,
    DictionaryItemCreate,
    DictionaryItemUpdate,
    DictionaryItemResponse
)

# 创建日志记录器
logger = logging.getLogger(__name__)

# 尝试导入缓存服务，如果失败则使用空缓存
try:
    from src.services.dictionary_cache import dictionary_cache
except ImportError as e:
    logger.warning(f"Failed to import dictionary cache: {e}")
    dictionary_cache = None
logger = logging.getLogger(__name__)

class DictionaryService:
    """
    字典管理服务
    处理字典和字典项的CRUD操作，支持树形结构查询和依赖检查
    """
    
    def __init__(self):
        logger.info("DictionaryService initialized")
        
    def _get_cached_dictionaries(self, page: int = 1, page_size: int = 10, search: Optional[str] = None, status: Optional[bool] = None, parent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取字典列表
        """
        if dictionary_cache is None:
            return None
        return dictionary_cache.get_dictionaries(page, page_size, search, status, parent_id)
    
    def _set_cached_dictionaries(self, data: Dict[str, Any]):
        """
        将字典列表设置到缓存中
        """
        if dictionary_cache is not None:
            dictionary_cache.set_dictionaries(data)
    
    def _get_cached_dictionaries_tree(self) -> Optional[List[Dict[str, Any]]]:
        """
        从缓存中获取字典树形结构
        """
        if dictionary_cache is None:
            return None
        return dictionary_cache.get_dictionaries_tree()
    
    def _set_cached_dictionaries_tree(self, data: List[Dict[str, Any]]):
        """
        将字典树形结构设置到缓存中
        """
        if dictionary_cache is not None:
            dictionary_cache.set_dictionaries_tree(data)
    
    def _get_cached_dictionary_items(self, dictionary_id: str, page: int = 1, page_size: int = 10, search: Optional[str] = None, status: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取字典项列表
        """
        if dictionary_cache is None:
            return None
        return dictionary_cache.get_dictionary_items(dictionary_id, page, page_size, search, status)
    
    def _set_cached_dictionary_items(self, dictionary_id: str, data: Dict[str, Any]):
        """
        将字典项列表设置到缓存中
        """
        if dictionary_cache is not None:
            dictionary_cache.set_dictionary_items(dictionary_id, data)
    
    def _get_cached_dictionary(self, dict_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取单个字典详情
        """
        if dictionary_cache is None:
            return None
        return dictionary_cache.get_dictionary(dict_id)
    
    def _set_cached_dictionary(self, dict_id: str, data: Dict[str, Any]):
        """
        将单个字典详情设置到缓存中
        """
        if dictionary_cache is not None:
            dictionary_cache.set_dictionary(dict_id, data)
    
    def _get_cached_dictionary_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        从缓存中获取单个字典项
        """
        if dictionary_cache is None:
            return None
        return dictionary_cache.get_dictionary_item(item_id)
    
    def _set_cached_dictionary_item(self, item_id: str, data: Dict[str, Any]):
        """
        将单个字典项设置到缓存中
        """
        if dictionary_cache is not None:
            dictionary_cache.set_dictionary_item(item_id, data)
    
    def _clear_dictionary_cache(self, dict_id: str = None):
        """
        清除字典缓存
        """
        if dictionary_cache is not None:
            dictionary_cache.clear_dictionary_cache(dict_id)
    
    def get_all_dictionaries(
        self,
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[bool] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取字典列表（支持分页、搜索、筛选）
        
        Args:
            db: 数据库会话
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（匹配编码或名称）
            status: 启用状态筛选
            parent_id: 父字典ID筛选
            
        Returns:
            包含items和total的字典
        """
        logger.info(f"Getting dictionaries with page={page}, page_size={page_size}, search={search}, status={status}, parent_id={parent_id}")
        
        # 尝试从缓存获取
        cached_data = self._get_cached_dictionaries(page, page_size, search, status, parent_id)
        if cached_data:
            logger.info("Returning dictionaries from cache")
            return cached_data
        
        # 构建查询
        query = db.query(Dictionary)
        
        # 搜索条件：匹配编码或名称
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                and_(
                    Dictionary.code.ilike(search_pattern),
                    Dictionary.name.ilike(search_pattern)
                )
            )
        
        # 状态筛选
        if status is not None:
            query = query.filter(Dictionary.status == status)
        
        # 父字典筛选
        if parent_id:
            query = query.filter(Dictionary.parent_id == parent_id)
        
        # 计算总数
        total = query.count()
        
        # 应用分页
        offset = (page - 1) * page_size
        dictionaries = query.order_by(Dictionary.sort_order, Dictionary.created_at).offset(offset).limit(page_size).all()
        
        # 转换为响应模型
        dict_list = [d.to_dict() for d in dictionaries]
        
        result = {
            "items": dict_list,
            "total": total
        }
        
        # 缓存结果
        self._set_cached_dictionaries(result)
        
        return result
    
    def get_dictionaries_tree(self, db: Session, status: Optional[bool] = None) -> List[Dict[str, Any]]:
        """
        获取字典树形结构
        
        递归构建完整的层级树，包含所有子字典
        
        Args:
            db: 数据库会话
            status: 启用状态筛选（可选）
            
        Returns:
            树形结构的字典列表
        """
        logger.info(f"Getting dictionaries tree with status filter: {status}")
        
        # 尝试从缓存获取
        cached_data = self._get_cached_dictionaries_tree()
        if cached_data:
            logger.info("Returning dictionaries tree from cache")
            return cached_data
        
        # 获取所有字典（按排序顺序）
        query = db.query(Dictionary).order_by(Dictionary.sort_order, Dictionary.created_at)
        
        if status is not None:
            query = query.filter(Dictionary.status == status)
        
        all_dicts = query.all()
        
        # 将字典转换为字典映射，便于查找
        dict_map = {d.id: d.to_dict() for d in all_dicts}
        
        # 构建树形结构
        tree = []
        
        # 遍历所有字典，构建树结构
        for dict_id, dict_info in dict_map.items():
            # 如果有父字典，将其添加到父字典的children中
            if dict_info['parent_id'] and dict_info['parent_id'] in dict_map:
                parent_info = dict_map[dict_info['parent_id']]
                if 'children' not in parent_info:
                    parent_info['children'] = []
                parent_info['children'].append(dict_info)
            else:
                # 顶级字典
                tree.append(dict_info)
        
        # 按排序顺序对每个节点的子节点进行排序
        def sort_children(node):
            if 'children' in node:
                node['children'].sort(key=lambda x: (x['sort_order'], x['created_at']))
                for child in node['children']:
                    sort_children(child)
        
        # 对树中的每个节点递归排序
        for node in tree:
            sort_children(node)
        
        logger.info(f"Built tree with {len(tree)} top-level nodes")
        
        # 缓存结果
        self._set_cached_dictionaries_tree(tree)
        
        return tree
    
    def get_dictionary_by_id(self, db: Session, dict_id: str) -> Optional[Dictionary]:
        """
        根据ID获取字典
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            
        Returns:
            Dictionary对象或None
        """
        logger.info(f"Getting dictionary by ID: {dict_id}")
        
        # 尝试从缓存获取
        cached_data = self._get_cached_dictionary(dict_id)
        if cached_data:
            logger.info("Returning dictionary from cache")
            # 从缓存中获取的数据是字典格式，需要转换为Dictionary对象
            # 由于我们只需要返回对象，这里直接从数据库获取
            # 在实际应用中，可以考虑缓存完整的对象
            pass
        
        return db.query(Dictionary).filter(Dictionary.id == dict_id).first()
    
    def get_dictionary_by_code(self, db: Session, code: str) -> Optional[Dictionary]:
        """
        根据编码获取字典
        
        Args:
            db: 数据库会话
            code: 字典编码
            
        Returns:
            Dictionary对象或None
        """
        logger.info(f"Getting dictionary by code: {code}")
        
        # 尝试从缓存获取
        # 由于缓存基于ID，这里直接查询数据库
        return db.query(Dictionary).filter(Dictionary.code == code).first()
    
    def create_dictionary(self, db: Session, dict_data: DictionaryCreate) -> Dictionary:
        """
        创建字典
        
        Args:
            db: 数据库会话
            dict_data: 字典创建数据
            
        Returns:
            创建的Dictionary对象
        """
        logger.info(f"Creating dictionary: {dict_data.name} (code: {dict_data.code})")
        
        # 创建字典对象
        db_dict = Dictionary(
            code=dict_data.code,
            name=dict_data.name,
            parent_id=dict_data.parent_id,
            description=dict_data.description,
            dict_type=dict_data.dict_type,
            status=dict_data.status,
            sort_order=dict_data.sort_order,
            created_by=dict_data.created_by
        )
        
        db.add(db_dict)
        db.commit()
        db.refresh(db_dict)
        
        logger.info(f"Dictionary created successfully: {dict_data.name} (ID: {db_dict.id})")
        
        # 清除相关缓存
        self._clear_dictionary_cache()
        
        return db_dict
    
    def update_dictionary(self, db: Session, dict_id: str, dict_data: DictionaryUpdate) -> Dictionary:
        """
        更新字典
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            dict_data: 字典更新数据
            
        Returns:
            更新后的Dictionary对象
        """
        logger.info(f"Updating dictionary {dict_id}")
        
        # 获取现有字典
        db_dict = db.query(Dictionary).filter(Dictionary.id == dict_id).first()
        if not db_dict:
            raise ValueError(f"字典不存在: {dict_id}")
        
        # 更新字段（只更新非None的值）
        if dict_data.code is not None:
            db_dict.code = dict_data.code
        if dict_data.name is not None:
            db_dict.name = dict_data.name
        if dict_data.parent_id is not None:
            db_dict.parent_id = dict_data.parent_id
        if dict_data.description is not None:
            db_dict.description = dict_data.description
        if dict_data.dict_type is not None:
            db_dict.dict_type = dict_data.dict_type
        if dict_data.status is not None:
            db_dict.status = dict_data.status
        if dict_data.sort_order is not None:
            db_dict.sort_order = dict_data.sort_order
        if dict_data.created_by is not None:
            db_dict.created_by = dict_data.created_by
        
        db.commit()
        db.refresh(db_dict)
        
        logger.info(f"Dictionary {dict_id} updated successfully")
        
        # 清除相关缓存
        self._clear_dictionary_cache(dict_id)
        
        return db_dict
    
    def delete_dictionary(self, db: Session, dict_id: str) -> bool:
        """
        删除字典
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            
        Returns:
            是否删除成功
        """
        logger.info(f"Deleting dictionary {dict_id}")
        
        # 获取字典
        db_dict = db.query(Dictionary).filter(Dictionary.id == dict_id).first()
        if not db_dict:
            return False
        
        # 删除字典
        db.delete(db_dict)
        db.commit()
        
        logger.info(f"Dictionary {dict_id} deleted successfully")
        
        # 清除相关缓存
        self._clear_dictionary_cache(dict_id)
        
        return True
    
    def get_dictionary_items(
        self,
        db: Session,
        dictionary_id: str,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        status: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        获取字典项列表（支持分页、搜索、筛选）
        
        Args:
            db: 数据库会话
            dictionary_id: 字典ID
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（匹配键值或值）
            status: 启用状态筛选
            
        Returns:
            包含items和total的字典
        """
        logger.info(f"Getting dictionary items for {dictionary_id} with page={page}, page_size={page_size}, search={search}, status={status}")
        
        # 验证字典是否存在
        dictionary = db.query(Dictionary).filter(Dictionary.id == dictionary_id).first()
        if not dictionary:
            raise ValueError(f"字典不存在: {dictionary_id}")
        
        # 🔧 CACHE FIX: Skip cache for now to ensure fresh data
        # This fixes the issue where cached empty results prevent new dictionary items from being displayed
        logger.info(f"🔧 CACHE FIX: Bypassing cache to get fresh dictionary items for {dictionary_id}")
        
        # 构建查询
        query = db.query(DictionaryItem).filter(DictionaryItem.dictionary_id == dictionary_id)
        
        # 搜索条件：匹配键值或值
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                and_(
                    DictionaryItem.item_key.ilike(search_pattern),
                    DictionaryItem.item_value.ilike(search_pattern)
                )
            )
        
        # 状态筛选
        if status is not None:
            query = query.filter(DictionaryItem.status == status)
        
        # 计算总数
        total = query.count()
        logger.info(f"🔧 CACHE FIX: Found {total} dictionary items in database for {dictionary_id}")
        
        # 应用分页
        offset = (page - 1) * page_size
        items = query.order_by(DictionaryItem.sort_order, DictionaryItem.created_at).offset(offset).limit(page_size).all()
        
        # 转换为响应模型
        item_list = [item.to_dict() for item in items]
        logger.info(f"🔧 CACHE FIX: Returning {len(item_list)} dictionary items for {dictionary_id}")
        
        result = {
            "items": item_list,
            "total": total
        }
        
        # 🔧 CACHE FIX: Don't cache the result to ensure fresh data
        # self._set_cached_dictionary_items(dictionary_id, result)
        
        return result
    
    def get_dictionary_item_by_id(self, db: Session, item_id: str) -> Optional[DictionaryItem]:
        """
        根据ID获取字典项
        
        Args:
            db: 数据库会话
            item_id: 字典项ID
            
        Returns:
            DictionaryItem对象或None
        """
        logger.info(f"Getting dictionary item by ID: {item_id}")
        
        # 尝试从缓存获取
        cached_data = self._get_cached_dictionary_item(item_id)
        if cached_data:
            logger.info("Returning dictionary item from cache")
            # 由于缓存是字典格式，这里直接从数据库获取对象
            pass
        
        return db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
    
    def get_dictionary_item_by_key(self, db: Session, dictionary_id: str, item_key: str) -> Optional[DictionaryItem]:
        """
        根据字典ID和键值获取字典项
        
        Args:
            db: 数据库会话
            dictionary_id: 字典ID
            item_key: 键值
            
        Returns:
            DictionaryItem对象或None
        """
        logger.info(f"Getting dictionary item by key {item_key} in dictionary {dictionary_id}")
        
        # 尝试从缓存获取
        # 由于缓存基于ID，这里直接查询数据库
        return db.query(DictionaryItem).filter(
            DictionaryItem.dictionary_id == dictionary_id,
            DictionaryItem.item_key == item_key
        ).first()
    
    def create_dictionary_item(self, db: Session, dictionary_id: str, item_data: DictionaryItemCreate) -> DictionaryItem:
        """
        创建字典项
        
        Args:
            db: 数据库会话
            dictionary_id: 字典ID
            item_data: 字典项创建数据
            
        Returns:
            创建的DictionaryItem对象
        """
        logger.info(f"Creating dictionary item for {dictionary_id}: {item_data.item_key} -> {item_data.item_value}")
        
        # 验证字典是否存在
        dictionary = db.query(Dictionary).filter(Dictionary.id == dictionary_id).first()
        if not dictionary:
            raise ValueError(f"字典不存在: {dictionary_id}")
        
        # 创建字典项对象
        db_item = DictionaryItem(
            dictionary_id=dictionary_id,
            item_key=item_data.item_key,
            item_value=item_data.item_value,
            description=item_data.description,
            sort_order=item_data.sort_order,
            status=item_data.status,
            extra_data=item_data.extra_data,
            created_by=getattr(item_data, 'created_by', 'system')  # 默认使用 'system' 如果没有提供
        )
        
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Dictionary item created successfully: {item_data.item_key} (ID: {db_item.id})")
        
        # 🔧 CACHE FIX: Clear all dictionary cache to ensure fresh data
        logger.info(f"🔧 CACHE FIX: Clearing all dictionary cache after creating item for {dictionary_id}")
        self._clear_dictionary_cache()  # Clear all cache, not just specific dictionary
        
        return db_item
    
    def update_dictionary_item(self, db: Session, item_id: str, item_data: DictionaryItemUpdate) -> DictionaryItem:
        """
        更新字典项
        
        Args:
            db: 数据库会话
            item_id: 字典项ID
            item_data: 字典项更新数据
            
        Returns:
            更新后的DictionaryItem对象
        """
        logger.info(f"Updating dictionary item {item_id}")
        
        # 获取现有字典项
        db_item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
        if not db_item:
            raise ValueError(f"字典项不存在: {item_id}")
        
        # 更新字段（只更新非None的值）
        if item_data.item_key is not None:
            db_item.item_key = item_data.item_key
        if item_data.item_value is not None:
            db_item.item_value = item_data.item_value
        if item_data.description is not None:
            db_item.description = item_data.description
        if item_data.sort_order is not None:
            db_item.sort_order = item_data.sort_order
        if item_data.status is not None:
            db_item.status = item_data.status
        if item_data.extra_data is not None:
            db_item.extra_data = item_data.extra_data
        
        db.commit()
        db.refresh(db_item)
        
        logger.info(f"Dictionary item {item_id} updated successfully")
        
        # 清除相关缓存
        # 获取字典ID
        dictionary_id = db_item.dictionary_id
        self._clear_dictionary_cache(dictionary_id)
        
        return db_item
    
    def delete_dictionary_item(self, db: Session, item_id: str) -> bool:
        """
        删除字典项
        
        Args:
            db: 数据库会话
            item_id: 字典项ID
            
        Returns:
            是否删除成功
        """
        logger.info(f"Deleting dictionary item {item_id}")
        
        # 获取字典项
        db_item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
        if not db_item:
            logger.warning(f"Dictionary item {item_id} not found for deletion")
            return False
        
        # 记录字典ID用于清除缓存
        dictionary_id = db_item.dictionary_id
        
        # 删除字典项
        db.delete(db_item)
        db.commit()
        
        logger.info(f"Dictionary item {item_id} deleted successfully from dictionary {dictionary_id}")
        
        # 🔧 CACHE FIX: Clear all dictionary cache after deletion
        logger.info(f"🔧 CACHE FIX: Clearing all dictionary cache after deleting item {item_id}")
        self._clear_dictionary_cache()  # Clear all cache, not just specific dictionary
        
        return True
    
    def has_children(self, db: Session, dict_id: str) -> bool:
        """
        检查字典是否有子字典
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            
        Returns:
            是否有子字典
        """
        logger.info(f"Checking if dictionary {dict_id} has children")
        
        count = db.query(Dictionary).filter(Dictionary.parent_id == dict_id).count()
        return count > 0
    
    def has_field_references(self, db: Session, dict_id: str) -> bool:
        """
        检查字典是否被字段引用
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            
        Returns:
            是否被字段引用
        """
        logger.info(f"Checking if dictionary {dict_id} has field references")
        
        count = db.query(TableField).filter(TableField.dictionary_id == dict_id).count()
        return count > 0
    
    def has_dynamic_configs(self, db: Session, dict_id: str) -> bool:
        """
        检查字典是否有关联的动态字典配置
        
        Args:
            db: 数据库会话
            dict_id: 字典ID
            
        Returns:
            是否有关联的动态配置
        """
        logger.info(f"Checking if dictionary {dict_id} has dynamic configurations")
        
        count = db.query(DynamicDictionaryConfig).filter(DynamicDictionaryConfig.dictionary_id == dict_id).count()
        return count > 0
    
    def is_ancestor(self, db: Session, ancestor_id: str, child_id: str) -> bool:
        """
        检查一个字典是否是另一个字典的祖先（递归检查）
        
        Args:
            db: 数据库会话
            ancestor_id: 祖先字典ID
            child_id: 子字典ID
            
        Returns:
            是否是祖先
        """
        logger.info(f"Checking if {ancestor_id} is ancestor of {child_id}")
        
        # 如果是直接父级，直接返回True
        if child_id == ancestor_id:
            return True
        
        # 获取当前字典的父字典
        current_dict = db.query(Dictionary).filter(Dictionary.id == child_id).first()
        if not current_dict:
            return False
        
        # 如果父字典是目标祖先，返回True
        if current_dict.parent_id == ancestor_id:
            return True
        
        # 如果有父字典，递归检查父字典
        if current_dict.parent_id:
            return self.is_ancestor(db, ancestor_id, current_dict.parent_id)
        
        # 没有父字典或未找到祖先
        return False