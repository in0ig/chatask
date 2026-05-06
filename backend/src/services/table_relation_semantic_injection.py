"""
表关联语义注入服务

实现表间关联关系的智能发现和注入，支持JOIN类型的自动识别和推荐（INNER/LEFT/RIGHT/FULL），
添加关联路径的语义描述和业务逻辑说明，创建多表查询的最优关联路径算法。
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
# import networkx as nx  # 暂时移除networkx依赖

logger = logging.getLogger(__name__)


class JoinType(str, Enum):
    """JOIN类型枚举"""
    INNER = "INNER JOIN"
    LEFT = "LEFT JOIN"
    RIGHT = "RIGHT JOIN"
    FULL = "FULL OUTER JOIN"
    CROSS = "CROSS JOIN"


class RelationType(str, Enum):
    """关联关系类型枚举"""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


@dataclass
class TableRelation:
    """表关联关系"""
    from_table: str
    to_table: str
    from_field: str
    to_field: str
    relation_type: RelationType
    join_type: JoinType
    confidence: float
    business_description: str


@dataclass
class JoinPath:
    """关联路径"""
    tables: List[str]
    relations: List[TableRelation]
    total_cost: float
    path_description: str


class TableRelationSemanticInjectionService:
    """表关联语义注入服务"""
    
    def __init__(self, db_session=None):
        self.db = db_session
        
        # JOIN类型语义描述
        self.join_semantics = {
            JoinType.INNER: "内连接，返回两表都有匹配记录的数据",
            JoinType.LEFT: "左连接，返回左表所有记录和右表匹配记录",
            JoinType.RIGHT: "右连接，返回右表所有记录和左表匹配记录",
            JoinType.FULL: "全外连接，返回两表所有记录",
            JoinType.CROSS: "交叉连接，返回两表的笛卡尔积"
        }
        
        # 字段名匹配模式
        self.field_patterns = {
            "id": ["id", "pk", "key"],
            "foreign_key": ["_id", "_key", "_ref"],
            "code": ["code", "no", "num"],
            "name": ["name", "title", "label"]
        }
    
    def inject_table_relation_semantics(
        self,
        table_ids: Optional[List[str]] = None,
        table_names: Optional[List[str]] = None
    ) -> List[TableRelation]:
        """
        注入表关联语义信息
        
        Args:
            table_ids: 表ID列表
            table_names: 表名列表
            
        Returns:
            表关联关系列表
        """
        try:
            # 获取表结构信息
            tables_info = self._get_tables_structure(table_ids, table_names)
            
            # 发现关联关系
            relations = self._discover_relations(tables_info)
            
            # 增强关联语义
            enhanced_relations = []
            for relation in relations:
                enhanced_relation = self._enhance_relation_semantics(relation)
                enhanced_relations.append(enhanced_relation)
            
            return enhanced_relations
            
        except Exception as e:
            logger.error(f"表关联语义注入失败: {str(e)}", exc_info=True)
            return []
    
    def _get_tables_structure(self, table_ids: Optional[List[str]], table_names: Optional[List[str]]) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        try:
            # 这里应该查询数据库获取表结构
            # 暂时返回模拟数据
            tables = []
            
            if table_ids:
                for table_id in table_ids:
                    tables.append({
                        "id": table_id,
                        "name": f"table_{table_id}",
                        "fields": [
                            {"name": "id", "type": "int", "is_primary": True},
                            {"name": "name", "type": "varchar", "is_primary": False}
                        ]
                    })
            
            if table_names:
                for table_name in table_names:
                    tables.append({
                        "id": table_name,
                        "name": table_name,
                        "fields": [
                            {"name": "id", "type": "int", "is_primary": True}
                        ]
                    })
            
            return tables
            
        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return []
    
    def _discover_relations(self, tables_info: List[Dict[str, Any]]) -> List[TableRelation]:
        """发现表间关联关系"""
        relations = []
        
        try:
            # 外键关系发现
            fk_relations = self._discover_foreign_key_relations(tables_info)
            relations.extend(fk_relations)
            
            # 字段名模式匹配
            pattern_relations = self._discover_pattern_relations(tables_info)
            relations.extend(pattern_relations)
            
            # 业务模式识别
            business_relations = self._discover_business_relations(tables_info)
            relations.extend(business_relations)
            
            return relations
            
        except Exception as e:
            logger.error(f"发现关联关系失败: {str(e)}")
            return []
    
    def _discover_foreign_key_relations(self, tables_info: List[Dict[str, Any]]) -> List[TableRelation]:
        """发现外键关系（使用真实数据库数据）"""
        relations = []
        
        try:
            if not self.db:
                logger.warning("数据库会话未初始化，无法查询外键关系")
                return relations
            
            # 从 table_relations 表中查询关联关系
            from src.models.data_preparation_model import TableRelation as DBTableRelation
            
            # 获取所有表的ID
            table_ids = [t.get("id") for t in tables_info if t.get("id")]
            
            if not table_ids:
                logger.warning("没有有效的表ID，无法查询关联关系")
                return relations
            
            # 查询涉及这些表的所有关联关系
            db_relations = self.db.query(DBTableRelation).filter(
                (DBTableRelation.source_table_id.in_(table_ids)) |
                (DBTableRelation.target_table_id.in_(table_ids))
            ).all()
            
            logger.info(f"从数据库查询到 {len(db_relations)} 条表关联关系")
            
            # 转换为 TableRelation 对象
            for db_rel in db_relations:
                # 获取源表和目标表的名称
                source_table = next((t for t in tables_info if t.get("id") == db_rel.source_table_id), None)
                target_table = next((t for t in tables_info if t.get("id") == db_rel.target_table_id), None)
                
                if not source_table or not target_table:
                    continue
                
                # 映射关联类型
                relation_type = self._map_relation_type(db_rel.relation_type)
                
                # 推荐JOIN类型
                join_type = self._recommend_join_type_from_relation_type(relation_type)
                
                relations.append(TableRelation(
                    from_table=source_table["name"],
                    to_table=target_table["name"],
                    from_field=db_rel.source_field or "id",
                    to_field=db_rel.target_field or "id",
                    relation_type=relation_type,
                    join_type=join_type,
                    confidence=0.95,  # 数据库定义的关联关系置信度高
                    business_description=db_rel.description or "数据库定义的关联关系"
                ))
            
            logger.info(f"成功转换 {len(relations)} 条表关联关系")
            return relations
            
        except Exception as e:
            logger.error(f"发现外键关系失败: {str(e)}", exc_info=True)
            return []
    
    def _discover_pattern_relations(self, tables_info: List[Dict[str, Any]]) -> List[TableRelation]:
        """基于字段名模式发现关联关系"""
        relations = []
        
        try:
            for i, table1 in enumerate(tables_info):
                for j, table2 in enumerate(tables_info):
                    if i >= j:
                        continue
                    
                    # 查找可能的关联字段
                    potential_relations = self._find_potential_field_matches(table1, table2)
                    
                    for relation in potential_relations:
                        relations.append(TableRelation(
                            from_table=table1["name"],
                            to_table=table2["name"],
                            from_field=relation["field1"],
                            to_field=relation["field2"],
                            relation_type=RelationType.ONE_TO_MANY,
                            join_type=JoinType.LEFT,
                            confidence=relation["confidence"],
                            business_description=f"基于字段名模式的关联：{relation['pattern']}"
                        ))
            
            return relations
            
        except Exception as e:
            logger.error(f"发现模式关系失败: {str(e)}")
            return []
    
    def _find_potential_field_matches(self, table1: Dict[str, Any], table2: Dict[str, Any]) -> List[Dict[str, Any]]:
        """查找潜在的字段匹配"""
        matches = []
        
        try:
            fields1 = {f["name"]: f for f in table1["fields"]}
            fields2 = {f["name"]: f for f in table2["fields"]}
            
            # 完全匹配
            for field_name in fields1:
                if field_name in fields2:
                    matches.append({
                        "field1": field_name,
                        "field2": field_name,
                        "pattern": "完全匹配",
                        "confidence": 0.8
                    })
            
            # 外键模式匹配
            for field1_name, field1 in fields1.items():
                for field2_name, field2 in fields2.items():
                    if self._is_foreign_key_pattern(field1_name, field2_name, table1["name"], table2["name"]):
                        matches.append({
                            "field1": field1_name,
                            "field2": field2_name,
                            "pattern": "外键模式",
                            "confidence": 0.7
                        })
            
            return matches
            
        except Exception as e:
            logger.error(f"查找字段匹配失败: {str(e)}")
            return []
    
    def _is_foreign_key_pattern(self, field1: str, field2: str, table1: str, table2: str) -> bool:
        """判断是否为外键模式"""
        # 检查是否为 table_name + _id 的模式
        if field1 == f"{table2}_id" and field2 == "id":
            return True
        if field2 == f"{table1}_id" and field1 == "id":
            return True
        
        # 检查其他外键模式
        fk_suffixes = ["_id", "_key", "_ref"]
        for suffix in fk_suffixes:
            if field1.endswith(suffix) and field2 == "id":
                return True
            if field2.endswith(suffix) and field1 == "id":
                return True
        
        return False
    
    def _discover_business_relations(self, tables_info: List[Dict[str, Any]]) -> List[TableRelation]:
        """发现业务关联关系"""
        relations = []
        
        try:
            # 基于表名推断业务关系
            for i, table1 in enumerate(tables_info):
                for j, table2 in enumerate(tables_info):
                    if i >= j:
                        continue
                    
                    business_relation = self._infer_business_relation(table1["name"], table2["name"])
                    if business_relation:
                        relations.append(business_relation)
            
            return relations
            
        except Exception as e:
            logger.error(f"发现业务关系失败: {str(e)}")
            return []
    
    def _infer_business_relation(self, table1: str, table2: str) -> Optional[TableRelation]:
        """推断业务关联关系"""
        table1_lower = table1.lower()
        table2_lower = table2.lower()
        
        # 用户-订单关系
        if ("user" in table1_lower and "order" in table2_lower) or ("order" in table1_lower and "user" in table2_lower):
            return TableRelation(
                from_table=table1,
                to_table=table2,
                from_field="user_id" if "order" in table1_lower else "id",
                to_field="id" if "order" in table1_lower else "user_id",
                relation_type=RelationType.ONE_TO_MANY,
                join_type=JoinType.LEFT,
                confidence=0.6,
                business_description="用户与订单的业务关联关系"
            )
        
        # 产品-订单关系
        if ("product" in table1_lower and "order" in table2_lower) or ("order" in table1_lower and "product" in table2_lower):
            return TableRelation(
                from_table=table1,
                to_table=table2,
                from_field="product_id" if "order" in table1_lower else "id",
                to_field="id" if "order" in table1_lower else "product_id",
                relation_type=RelationType.MANY_TO_MANY,
                join_type=JoinType.INNER,
                confidence=0.6,
                business_description="产品与订单的业务关联关系"
            )
        
        return None
    
    def _enhance_relation_semantics(self, relation: TableRelation) -> TableRelation:
        """增强关联关系语义"""
        try:
            # 推荐最佳JOIN类型
            recommended_join = self._recommend_join_type(relation)
            relation.join_type = recommended_join
            
            # 生成业务逻辑说明
            if not relation.business_description:
                relation.business_description = self._generate_business_description(relation)
            
            return relation
            
        except Exception as e:
            logger.error(f"增强关联语义失败: {str(e)}")
            return relation
    
    def _recommend_join_type(self, relation: TableRelation) -> JoinType:
        """推荐JOIN类型"""
        # 基于关联类型推荐JOIN类型
        if relation.relation_type == RelationType.ONE_TO_ONE:
            return JoinType.INNER
        elif relation.relation_type == RelationType.ONE_TO_MANY:
            return JoinType.LEFT
        elif relation.relation_type == RelationType.MANY_TO_ONE:
            return JoinType.LEFT
        elif relation.relation_type == RelationType.MANY_TO_MANY:
            return JoinType.INNER
        else:
            return JoinType.LEFT
    
    def _map_relation_type(self, db_relation_type: str) -> RelationType:
        """映射数据库关联类型到枚举类型"""
        if not db_relation_type:
            return RelationType.ONE_TO_MANY
        
        relation_type_lower = db_relation_type.lower()
        
        if "one_to_one" in relation_type_lower or "1:1" in relation_type_lower:
            return RelationType.ONE_TO_ONE
        elif "one_to_many" in relation_type_lower or "1:n" in relation_type_lower:
            return RelationType.ONE_TO_MANY
        elif "many_to_one" in relation_type_lower or "n:1" in relation_type_lower:
            return RelationType.MANY_TO_ONE
        elif "many_to_many" in relation_type_lower or "n:n" in relation_type_lower:
            return RelationType.MANY_TO_MANY
        else:
            return RelationType.ONE_TO_MANY
    
    def _recommend_join_type_from_relation_type(self, relation_type: RelationType) -> JoinType:
        """根据关联类型推荐JOIN类型"""
        if relation_type == RelationType.ONE_TO_ONE:
            return JoinType.INNER
        elif relation_type == RelationType.ONE_TO_MANY:
            return JoinType.LEFT
        elif relation_type == RelationType.MANY_TO_ONE:
            return JoinType.LEFT
        elif relation_type == RelationType.MANY_TO_MANY:
            return JoinType.INNER
        else:
            return JoinType.LEFT
    
    def _generate_business_description(self, relation: TableRelation) -> str:
        """生成业务逻辑说明"""
        join_desc = self.join_semantics.get(relation.join_type, "关联查询")
        return f"{relation.from_table}与{relation.to_table}通过{relation.from_field}和{relation.to_field}进行{join_desc}"
    
    def find_optimal_join_path(self, tables: List[str], relations: List[TableRelation]) -> Optional[JoinPath]:
        """查找最优关联路径"""
        try:
            if len(tables) < 2:
                return None
            
            # 构建关联图
            graph = self._build_relation_graph(relations)
            
            # 使用最短路径算法查找最优路径
            start_table = tables[0]
            target_tables = tables[1:]
            
            optimal_path = self._find_shortest_path(graph, start_table, target_tables)
            
            if optimal_path:
                return self._create_join_path(optimal_path, relations)
            
            return None
            
        except Exception as e:
            logger.error(f"查找最优路径失败: {str(e)}")
            return None
    
    def _build_relation_graph(self, relations: List[TableRelation]) -> Dict[str, List[Dict[str, Any]]]:
        """构建关联图（简化版，不使用networkx）"""
        graph = {}
        
        for relation in relations:
            # 使用置信度的倒数作为边的权重（置信度越高，权重越低）
            weight = 1.0 / max(relation.confidence, 0.1)
            
            # 添加双向边
            if relation.from_table not in graph:
                graph[relation.from_table] = []
            if relation.to_table not in graph:
                graph[relation.to_table] = []
            
            graph[relation.from_table].append({
                'target': relation.to_table,
                'weight': weight,
                'relation': relation
            })
            graph[relation.to_table].append({
                'target': relation.from_table,
                'weight': weight,
                'relation': relation
            })
        
        return graph
    
    def _find_shortest_path(self, graph: Dict[str, List[Dict[str, Any]]], start: str, targets: List[str]) -> Optional[List[str]]:
        """查找最短路径（简化版BFS算法）"""
        try:
            if start not in graph:
                return None
            
            # 使用BFS查找最短路径
            from collections import deque
            
            queue = deque([(start, [start])])
            visited = {start}
            found_targets = set()
            result_path = [start]
            
            while queue and len(found_targets) < len(targets):
                current, path = queue.popleft()
                
                if current in targets and current not in found_targets:
                    found_targets.add(current)
                    # 扩展结果路径
                    for node in path:
                        if node not in result_path:
                            result_path.append(node)
                
                if current in graph:
                    for edge in graph[current]:
                        neighbor = edge['target']
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append((neighbor, path + [neighbor]))
            
            return result_path if len(result_path) > 1 else None
            
        except Exception as e:
            logger.error(f"查找最短路径失败: {str(e)}")
            return None
    
    def _create_join_path(self, path: List[str], relations: List[TableRelation]) -> JoinPath:
        """创建JOIN路径"""
        path_relations = []
        total_cost = 0.0
        
        # 查找路径中每一步的关联关系
        for i in range(len(path) - 1):
            from_table = path[i]
            to_table = path[i + 1]
            
            # 查找对应的关联关系
            relation = self._find_relation(from_table, to_table, relations)
            if relation:
                path_relations.append(relation)
                total_cost += (1.0 - relation.confidence)
        
        # 生成路径描述
        path_description = self._generate_path_description(path, path_relations)
        
        return JoinPath(
            tables=path,
            relations=path_relations,
            total_cost=total_cost,
            path_description=path_description
        )
    
    def _find_relation(self, from_table: str, to_table: str, relations: List[TableRelation]) -> Optional[TableRelation]:
        """查找两表之间的关联关系"""
        for relation in relations:
            if (relation.from_table == from_table and relation.to_table == to_table) or \
               (relation.from_table == to_table and relation.to_table == from_table):
                return relation
        return None
    
    def _generate_path_description(self, path: List[str], relations: List[TableRelation]) -> str:
        """生成路径描述"""
        if not relations:
            return f"路径: {' -> '.join(path)}"
        
        descriptions = []
        for i, relation in enumerate(relations):
            join_desc = self.join_semantics.get(relation.join_type, "关联")
            descriptions.append(f"{relation.from_table} {join_desc} {relation.to_table}")
        
        return " -> ".join(descriptions)
    
    def generate_semantic_context(self, relations: List[TableRelation]) -> str:
        """生成表关联语义上下文"""
        if not relations:
            return "无表关联信息"
        
        context_parts = []
        
        for relation in relations:
            relation_context = [
                f"关联: {relation.from_table}.{relation.from_field} -> {relation.to_table}.{relation.to_field}",
                f"类型: {relation.relation_type.value}",
                f"JOIN: {relation.join_type.value}",
                f"置信度: {relation.confidence:.2f}",
                f"描述: {relation.business_description}"
            ]
            context_parts.append(" | ".join(relation_context))
        
        return "\n".join(context_parts)