from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import logging
from datetime import datetime, timedelta

from ..models.data_preparation_model import Dictionary, DictionaryItem, FieldMapping, DataTable, TableField
from ..database import get_db

logger = logging.getLogger(__name__)

class SemanticInjectionService:
    """数据字典语义注入服务
    
    负责将数据字典的语义信息注入到查询结果中，
    提供字段值的语义增强和解释。
    """
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = timedelta(minutes=30)
        self._last_cache_clear = datetime.now()
    
    def _clear_expired_cache(self):
        """清理过期缓存"""
        now = datetime.now()
        if now - self._last_cache_clear > self._cache_ttl:
            self._cache.clear()
            self._last_cache_clear = now
    
    def _get_cache_key(self, table_name: str, field_name: str) -> str:
        """生成缓存键"""
        return f"{table_name}.{field_name}"
    
    def get_field_semantic_mapping(self, db: Session, table_name: str, field_name: str) -> Optional[Dict[str, Any]]:
        """获取字段的语义映射信息
        
        Args:
            db: 数据库会话
            table_name: 表名
            field_name: 字段名
            
        Returns:
            字段的语义映射信息，包括字典信息和映射规则
        """
        try:
            self._clear_expired_cache()
            cache_key = self._get_cache_key(table_name, field_name)
            
            # 检查缓存
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            # 查询字段映射 - 通过表名和字段名查找
            field_mapping = db.query(FieldMapping).join(
                FieldMapping.table
            ).join(
                FieldMapping.field
            ).filter(
                FieldMapping.table.has(table_name=table_name),
                FieldMapping.field.has(field_name=field_name)
            ).first()
            
            if not field_mapping or not field_mapping.dictionary_id:
                return None
            
            # 查询关联的字典
            dictionary = db.query(Dictionary).filter(
                Dictionary.id == field_mapping.dictionary_id
            ).first()
            
            if not dictionary:
                return None
            
            # 查询字典项
            dictionary_items = db.query(DictionaryItem).filter(
                DictionaryItem.dictionary_id == dictionary.id
            ).all()
            
            # 构建语义映射
            semantic_mapping = {
                'dictionary_id': dictionary.id,
                'dictionary_name': dictionary.name,
                'dictionary_code': dictionary.code,
                'field_mapping_id': field_mapping.id,
                'mapping_type': 'direct',  # 默认映射类型
                'value_mappings': {},
                'metadata': {
                    'description': dictionary.description,
                    'created_at': dictionary.created_at.isoformat() if dictionary.created_at else None,
                    'updated_at': dictionary.updated_at.isoformat() if dictionary.updated_at else None
                }
            }
            
            # 构建值映射
            for item in dictionary_items:
                semantic_mapping['value_mappings'][item.code] = {
                    'label': item.name,
                    'description': item.description,
                    'sort_order': item.sort_order,
                    'is_active': item.is_active
                }
            
            # 缓存结果
            self._cache[cache_key] = semantic_mapping
            
            return semantic_mapping
            
        except Exception as e:
            logger.error(f"获取字段语义映射失败: {str(e)}")
            return None
    
    def inject_semantic_values(self, db: Session, table_name: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """为查询结果注入语义值
        
        Args:
            db: 数据库会话
            table_name: 表名
            data: 原始查询结果
            
        Returns:
            注入语义信息后的数据
        """
        if not data:
            return data
        
        try:
            # 获取表的所有字段映射 - 通过表名查找
            field_mappings = db.query(FieldMapping).join(
                FieldMapping.table
            ).join(
                FieldMapping.field
            ).filter(
                FieldMapping.table.has(table_name=table_name)
            ).all()
            
            if not field_mappings:
                return data
            
            # 为每个字段获取语义映射
            semantic_mappings = {}
            for mapping in field_mappings:
                field_name = mapping.field.field_name if mapping.field else None
                if field_name:
                    semantic_info = self.get_field_semantic_mapping(
                        db, table_name, field_name
                    )
                    if semantic_info:
                        semantic_mappings[field_name] = semantic_info
            
            # 注入语义值
            enhanced_data = []
            for row in data:
                enhanced_row = row.copy()
                semantic_row = {}
                
                for field_name, semantic_info in semantic_mappings.items():
                    if field_name in row:
                        original_value = row[field_name]
                        semantic_value = self._get_semantic_value(
                            original_value, semantic_info
                        )
                        semantic_row[f"{field_name}_semantic"] = semantic_value
                
                # 添加语义信息到行数据
                if semantic_row:
                    enhanced_row['_semantic'] = semantic_row
                
                enhanced_data.append(enhanced_row)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"注入语义值失败: {str(e)}")
            return data
    
    def _get_semantic_value(self, original_value: Any, semantic_info: Dict[str, Any]) -> Dict[str, Any]:
        """获取单个值的语义信息
        
        Args:
            original_value: 原始值
            semantic_info: 语义映射信息
            
        Returns:
            语义值信息
        """
        if original_value is None:
            return {
                'original_value': None,
                'semantic_label': None,
                'description': None,
                'dictionary_name': semantic_info.get('dictionary_name')
            }
        
        # 转换为字符串进行匹配
        value_key = str(original_value)
        value_mappings = semantic_info.get('value_mappings', {})
        
        if value_key in value_mappings:
            mapping = value_mappings[value_key]
            return {
                'original_value': original_value,
                'semantic_label': mapping.get('label'),
                'description': mapping.get('description'),
                'dictionary_name': semantic_info.get('dictionary_name'),
                'is_active': mapping.get('is_active', True)
            }
        else:
            return {
                'original_value': original_value,
                'semantic_label': None,
                'description': f"未找到值 '{original_value}' 的语义映射",
                'dictionary_name': semantic_info.get('dictionary_name'),
                'is_active': True
            }
    
    def get_table_semantic_schema(self, db: Session, table_name: str) -> Dict[str, Any]:
        """获取表的语义模式
        
        Args:
            db: 数据库会话
            table_name: 表名
            
        Returns:
            表的语义模式信息
        """
        try:
            # 获取表的所有字段映射 - 通过表名查找
            field_mappings = db.query(FieldMapping).join(
                FieldMapping.table
            ).join(
                FieldMapping.field
            ).filter(
                FieldMapping.table.has(table_name=table_name)
            ).all()
            
            schema = {
                'table_name': table_name,
                'semantic_fields': {},
                'metadata': {
                    'total_mapped_fields': len(field_mappings),
                    'generated_at': datetime.now().isoformat()
                }
            }
            
            for mapping in field_mappings:
                field_name = mapping.field.field_name if mapping.field else None
                if field_name:
                    semantic_info = self.get_field_semantic_mapping(
                        db, table_name, field_name
                    )
                    if semantic_info:
                        schema['semantic_fields'][field_name] = {
                            'dictionary_name': semantic_info.get('dictionary_name'),
                            'dictionary_code': semantic_info.get('dictionary_code'),
                            'mapping_type': semantic_info.get('mapping_type'),
                            'available_values': list(semantic_info.get('value_mappings', {}).keys())
                        }
            
            return schema
            
        except Exception as e:
            logger.error(f"获取表语义模式失败: {str(e)}")
            return {
                'table_name': table_name,
                'semantic_fields': {},
                'error': str(e)
            }
    
    def batch_inject_semantic_values(self, db: Session, table_data_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """批量为多个表的数据注入语义值
        
        Args:
            db: 数据库会话
            table_data_map: 表名到数据的映射
            
        Returns:
            注入语义信息后的数据映射
        """
        result = {}
        
        for table_name, data in table_data_map.items():
            try:
                enhanced_data = self.inject_semantic_values(db, table_name, data)
                result[table_name] = enhanced_data
            except Exception as e:
                logger.error(f"批量注入语义值失败 - 表 {table_name}: {str(e)}")
                result[table_name] = data  # 返回原始数据
        
        return result
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._last_cache_clear = datetime.now()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'cache_size': len(self._cache),
            'last_clear': self._last_cache_clear.isoformat(),
            'ttl_minutes': self._cache_ttl.total_seconds() / 60
        }

# 全局服务实例
semantic_injection_service = SemanticInjectionService()