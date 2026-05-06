"""
表关联验证服务
用于验证数据表之间的关联配置是否有效
"""
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from src.models.data_preparation_model import DataTable, TableField, TableRelation

class RelationValidator:
    """
    表关联验证服务类
    负责验证表关联配置的有效性
    """
    
    def __init__(self, db_session: Session):
        """
        初始化验证器
        
        Args:
            db_session: SQLAlchemy数据库会话
        """
        self.db_session = db_session
        
    def validate_field_types(self, primary_field_id: str, foreign_field_id: str) -> bool:
        """
        验证关联字段的数据类型是否匹配
        
        Args:
            primary_field_id: 主表字段ID
            foreign_field_id: 从表字段ID
            
        Returns:
            bool: 类型匹配返回True，不匹配返回False
        """
        # 查询主表字段
        primary_field = self.db_session.query(TableField).filter(
            TableField.id == primary_field_id
        ).first()
        
        # 查询从表字段
        foreign_field = self.db_session.query(TableField).filter(
            TableField.id == foreign_field_id
        ).first()
        
        # 如果任一字段不存在，返回False
        if not primary_field or not foreign_field:
            return False
        
        # 比较数据类型（忽略大小写）
        return primary_field.data_type.lower() == foreign_field.data_type.lower()
    
    def detect_circular_relations(self, relation_id: str, visited: Optional[Set[str]] = None, path: Optional[List[str]] = None) -> bool:
        """
        检测表关联是否形成环路
        使用深度优先搜索(DFS)检测环路
        
        Args:
            relation_id: 要检查的关联ID
            visited: 已访问的关联ID集合
            path: 当前路径
            
        Returns:
            bool: 存在环路返回True，不存在返回False
        """
        if visited is None:
            visited = set()
        if path is None:
            path = []
        
        # 获取当前关联
        current_relation = self.db_session.query(TableRelation).filter(
            TableRelation.id == relation_id
        ).first()
        
        if not current_relation:
            return False
        
        # 检查自关联
        if current_relation.primary_table_id == current_relation.foreign_table_id:
            return True
        
        # 检查是否在当前路径中已存在（形成环路）
        if relation_id in path:
            return True
        
        # 标记为已访问
        visited.add(relation_id)
        path.append(relation_id)
        
        # 递归检查从表作为主表的所有关联
        foreign_table_id = current_relation.foreign_table_id
        
        # 查询所有以当前从表作为主表的关联
        child_relations = self.db_session.query(TableRelation).filter(
            TableRelation.primary_table_id == foreign_table_id
        ).all()
        
        for child_relation in child_relations:
            if self.detect_circular_relations(child_relation.id, visited.copy(), path.copy()):
                return True
        
        return False
    
    def check_relation_dependencies(self, relation_id: str) -> List[str]:
        """
        检查关联依赖关系
        确保主表和从表都存在，且字段都存在
        
        Args:
            relation_id: 关联ID
            
        Returns:
            List[str]: 依赖问题列表，空列表表示无问题
        """
        issues = []
        
        # 获取关联配置
        relation = self.db_session.query(TableRelation).filter(
            TableRelation.id == relation_id
        ).first()
        
        if not relation:
            issues.append(f"关联ID {relation_id} 不存在")
            return issues
        
        # 检查主表是否存在
        if not self.db_session.query(DataTable).filter(
            DataTable.id == relation.primary_table_id
        ).first():
            issues.append(f"主表ID {relation.primary_table_id} 不存在")
        
        # 检查从表是否存在
        if not self.db_session.query(DataTable).filter(
            DataTable.id == relation.foreign_table_id
        ).first():
            issues.append(f"从表ID {relation.foreign_table_id} 不存在")
        
        # 检查主表字段是否存在
        if not self.db_session.query(TableField).filter(
            TableField.id == relation.primary_field_id
        ).first():
            issues.append(f"主表字段ID {relation.primary_field_id} 不存在")
        
        # 检查从表字段是否存在
        if not self.db_session.query(TableField).filter(
            TableField.id == relation.foreign_field_id
        ).first():
            issues.append(f"从表字段ID {relation.foreign_field_id} 不存在")
        
        # 检查主表字段是否属于主表
        primary_field = self.db_session.query(TableField).filter(
            TableField.id == relation.primary_field_id
        ).first()
        if primary_field and primary_field.table_id != relation.primary_table_id:
            issues.append(f"主表字段ID {relation.primary_field_id} 不属于主表ID {relation.primary_table_id}")
        
        # 检查从表字段是否属于从表
        foreign_field = self.db_session.query(TableField).filter(
            TableField.id == relation.foreign_field_id
        ).first()
        if foreign_field and foreign_field.table_id != relation.foreign_table_id:
            issues.append(f"从表字段ID {relation.foreign_field_id} 不属于从表ID {relation.foreign_table_id}")
        
        return issues
    
    def validate_relation(self, relation_id: str) -> Dict[str, any]:
        """
        综合验证关联配置
        
        Args:
            relation_id: 关联ID
            
        Returns:
            Dict[str, any]: 验证结果包含所有检查项的状态和问题
        """
        result = {
            "relation_id": relation_id,
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "field_types_match": False,
            "circular_relation": False,
            "dependencies_ok": True,
            "dependency_issues": []
        }
        
        # 检查依赖关系
        dependency_issues = self.check_relation_dependencies(relation_id)
        if dependency_issues:
            result["dependencies_ok"] = False
            result["dependency_issues"] = dependency_issues
            result["errors"].extend(dependency_issues)
            result["is_valid"] = False
        
        # 如果依赖有问题，跳过其他检查
        if not result["dependencies_ok"]:
            return result
        
        # 获取关联配置
        relation = self.db_session.query(TableRelation).filter(
            TableRelation.id == relation_id
        ).first()
        
        if not relation:
            result["errors"].append(f"关联ID {relation_id} 不存在")
            result["is_valid"] = False
            return result
        
        # 验证字段类型匹配
        result["field_types_match"] = self.validate_field_types(
            relation.primary_field_id, 
            relation.foreign_field_id
        )
        
        if not result["field_types_match"]:
            result["errors"].append(
                f"主表字段 {relation.primary_field_id} 和从表字段 {relation.foreign_field_id} 数据类型不匹配"
            )
            result["is_valid"] = False
        
        # 检测环路
        result["circular_relation"] = self.detect_circular_relations(relation_id)
        
        if result["circular_relation"]:
            result["errors"].append(
                f"关联 {relation_id} 形成环路，可能导致查询死循环"
            )
            result["is_valid"] = False
        
        return result
