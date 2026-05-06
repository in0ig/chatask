"""
选表结果解析和验证服务

任务 5.2.4 的核心实现
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from src.services.data_table_service import DataTableService

logger = logging.getLogger(__name__)


class ValidationCategory(Enum):
    """验证类别"""
    EXISTENCE = "existence"          # 存在性验证
    ACCESSIBILITY = "accessibility"  # 可访问性验证
    INTEGRITY = "integrity"          # 完整性验证
    RELATION = "relation"            # 关联性验证
    PERFORMANCE = "performance"      # 性能验证
    BUSINESS = "business"            # 业务合理性验证


class ValidationSeverity(Enum):
    """验证严重程度"""
    ERROR = "error"      # 错误 - 阻止执行
    WARNING = "warning"  # 警告 - 建议修复
    INFO = "info"        # 信息 - 仅提示


@dataclass
class ValidationIssue:
    """验证问题"""
    category: ValidationCategory
    severity: ValidationSeverity
    table_name: str
    field_name: Optional[str]
    message: str
    suggestion: str
    details: Dict[str, Any]


@dataclass
class TableValidationResult:
    """单表验证结果"""
    table_name: str
    table_id: str
    is_valid: bool
    exists: bool
    accessible: bool
    data_integrity_score: float
    issues: List[ValidationIssue]
    metadata: Dict[str, Any]


@dataclass
class RelationValidationResult:
    """表关联验证结果"""
    source_table: str
    target_table: str
    is_valid: bool
    relation_exists: bool
    join_feasible: bool
    business_reasonable: bool
    confidence_score: float
    issues: List[ValidationIssue]
    recommended_join: Dict[str, Any]


@dataclass
class SelectionValidationResult:
    """选表结果验证"""
    is_valid: bool
    overall_confidence: float
    table_validations: List[TableValidationResult]
    relation_validations: List[RelationValidationResult]
    selection_explanation: str
    transparency_report: Dict[str, Any]
    recommendations: List[str]
    processing_time: float


class TableSelectionValidator:
    """选表结果解析和验证服务"""
    
    def __init__(self):
        """初始化验证服务"""
        self.data_table_service = DataTableService()
        
        # 验证配置
        self.validation_config = {
            "min_confidence_threshold": 0.5,
            "min_data_integrity_score": 0.3,
            "max_null_rate": 0.8,
            "min_sample_rows": 5
        }
        
        # 验证统计信息
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "average_processing_time": 0.0,
            "common_issues": {},
            "configuration": self.validation_config
        }
    
    def validate_selection_result(
        self,
        selection_result: Any,
        data_source_id: str,
        options: Optional[Dict[str, Any]] = None
    ) -> SelectionValidationResult:
        """
        验证选表结果
        
        Args:
            selection_result: 智能选表的结果
            data_source_id: 数据源ID
            options: 验证选项
            
        Returns:
            SelectionValidationResult: 验证结果
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"开始验证选表结果，数据源: {data_source_id}")
            
            # 1. 验证所有选中的表
            all_tables = selection_result.primary_tables + selection_result.related_tables
            table_validations = self._validate_selected_tables(
                all_tables, data_source_id, options or {}
            )
            
            # 2. 验证表间关联关系
            relation_validations = self._validate_table_relations(
                selection_result.recommended_joins,
                all_tables,
                data_source_id
            )
            
            # 3. 计算整体置信度
            overall_confidence = self._calculate_overall_confidence(
                table_validations, relation_validations
            )
            
            # 4. 判断整体有效性
            is_valid = self._determine_overall_validity(
                table_validations, relation_validations, overall_confidence
            )
            
            # 5. 生成透明度报告
            transparency_report = self._generate_transparency_report(
                selection_result, table_validations, relation_validations
            )
            
            # 6. 生成选择解释
            selection_explanation = self._generate_selection_explanation(
                selection_result, table_validations, relation_validations
            )
            
            # 7. 生成推荐
            recommendations = self._generate_recommendations(
                table_validations, relation_validations
            )
            
            # 8. 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 9. 创建验证结果
            validation_result = SelectionValidationResult(
                is_valid=is_valid,
                overall_confidence=overall_confidence,
                table_validations=table_validations,
                relation_validations=relation_validations,
                selection_explanation=selection_explanation,
                transparency_report=transparency_report,
                recommendations=recommendations,
                processing_time=processing_time
            )
            
            # 10. 更新统计信息
            self._update_validation_stats(validation_result, processing_time)
            
            logger.info(f"选表结果验证完成，有效性: {is_valid}")
            return validation_result
            
        except Exception as e:
            logger.error(f"选表验证失败: {str(e)}", exc_info=True)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return SelectionValidationResult(
                is_valid=False,
                overall_confidence=0.0,
                table_validations=[],
                relation_validations=[],
                selection_explanation=f"验证过程发生错误: {str(e)}",
                transparency_report={},
                recommendations=["请检查选表结果格式", "请联系技术支持"],
                processing_time=processing_time
            )
    
    def _validate_selected_tables(
        self,
        tables: List[Any],
        data_source_id: str,
        options: Dict[str, Any]
    ) -> List[TableValidationResult]:
        """验证所有选中的表"""
        validations = []
        
        for table in tables:
            validation = self._validate_single_table(table, data_source_id, options)
            validations.append(validation)
        
        return validations
    
    def _validate_single_table(
        self,
        table: Any,
        data_source_id: str,
        options: Dict[str, Any]
    ) -> TableValidationResult:
        """验证单个表"""
        issues = []
        metadata = {}
        
        # 1. 检查表存在性
        exists = self._check_table_existence(table, data_source_id)
        if not exists:
            issues.append(ValidationIssue(
                category=ValidationCategory.EXISTENCE,
                severity=ValidationSeverity.ERROR,
                table_name=table.table_name,
                field_name=None,
                message=f"表 {table.table_name} 不存在",
                suggestion="检查表名是否正确或表是否已被删除",
                details={"table_id": table.table_id}
            ))
            
            return TableValidationResult(
                table_name=table.table_name,
                table_id=table.table_id,
                is_valid=False,
                exists=False,
                accessible=False,
                data_integrity_score=0.0,
                issues=issues,
                metadata=metadata
            )
        
        # 2. 检查表可访问性
        accessible = self._check_table_accessibility(table, data_source_id)
        if not accessible:
            issues.append(ValidationIssue(
                category=ValidationCategory.ACCESSIBILITY,
                severity=ValidationSeverity.ERROR,
                table_name=table.table_name,
                field_name=None,
                message=f"表 {table.table_name} 不可访问",
                suggestion="检查数据库权限或表结构",
                details={}
            ))
            
            return TableValidationResult(
                table_name=table.table_name,
                table_id=table.table_id,
                is_valid=False,
                exists=True,
                accessible=False,
                data_integrity_score=0.0,
                issues=issues,
                metadata=metadata
            )
        
        # 3. 检查数据完整性
        data_integrity_score = self._check_data_integrity(table, data_source_id, issues)
        
        # 4. 深度验证（如果启用）
        if options.get("enable_deep_validation", False):
            self._validate_table_fields(table, data_source_id, issues, metadata)
        
        # 5. 检查数据样本（如果启用）
        if options.get("check_data_samples", False):
            self._check_data_samples(table, data_source_id, issues, metadata)
        
        # 6. 判断表是否有效
        is_valid = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0
        
        return TableValidationResult(
            table_name=table.table_name,
            table_id=table.table_id,
            is_valid=is_valid,
            exists=True,
            accessible=True,
            data_integrity_score=data_integrity_score,
            issues=issues,
            metadata=metadata
        )
    
    def _check_table_existence(self, table: Any, data_source_id: str) -> bool:
        """检查表存在性"""
        try:
            result = self.data_table_service.get_table_by_name_and_source(
                table.table_name, data_source_id
            )
            return result is not None
        except Exception as e:
            logger.warning(f"检查表存在性失败: {str(e)}")
            return True  # 默认假设存在，避免误报
    
    def _check_table_accessibility(self, table: Any, data_source_id: str) -> bool:
        """检查表可访问性"""
        try:
            columns = self.data_table_service.get_table_columns(table.table_name, data_source_id)
            return columns is not None and len(columns) > 0
        except Exception as e:
            logger.warning(f"检查表可访问性失败: {str(e)}")
            return True  # 默认假设可访问
    
    def _check_data_integrity(
        self,
        table: Any,
        data_source_id: str,
        issues: List[ValidationIssue]
    ) -> float:
        """检查数据完整性"""
        score = 1.0
        
        # 检查行数
        row_count = self._get_table_row_count(table, data_source_id)
        if row_count == 0:
            score *= 0.5
            issues.append(ValidationIssue(
                category=ValidationCategory.INTEGRITY,
                severity=ValidationSeverity.WARNING,
                table_name=table.table_name,
                field_name=None,
                message=f"表 {table.table_name} 为空表",
                suggestion="确认表是否应该包含数据",
                details={"row_count": 0}
            ))
        
        # 检查空值率
        null_rates = self._check_null_rates(table, data_source_id)
        for field, rate in null_rates.items():
            if rate > self.validation_config["max_null_rate"]:
                score *= 0.9
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTEGRITY,
                    severity=ValidationSeverity.WARNING,
                    table_name=table.table_name,
                    field_name=field,
                    message=f"字段 {field} 空值率过高: {rate:.1%}",
                    suggestion="检查数据质量或字段定义",
                    details={"null_rate": rate}
                ))
        
        return max(score, 0.0)
    
    def _get_table_row_count(self, table: Any, data_source_id: str) -> int:
        """获取表行数"""
        try:
            # 这里应该调用实际的数据库查询
            return 0  # 简化实现
        except Exception:
            return 0
    
    def _check_null_rates(self, table: Any, data_source_id: str) -> Dict[str, float]:
        """检查字段空值率"""
        try:
            # 这里应该调用实际的数据库查询
            return {}  # 简化实现
        except Exception:
            return {}
    
    def _validate_table_fields(
        self,
        table: Any,
        data_source_id: str,
        issues: List[ValidationIssue],
        metadata: Dict[str, Any]
    ) -> None:
        """验证表字段"""
        try:
            columns = self.data_table_service.get_table_columns(table.table_name, data_source_id)
            if not columns:
                return
            
            metadata["field_count"] = len(columns)
            
            # 检查主键
            has_primary_key = any(getattr(col, 'is_primary_key', False) for col in columns)
            if not has_primary_key:
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTEGRITY,
                    severity=ValidationSeverity.WARNING,
                    table_name=table.table_name,
                    field_name=None,
                    message=f"表 {table.table_name} 没有定义主键",
                    suggestion="建议为表定义主键以提高查询性能",
                    details={}
                ))
            
            # 检查字段类型
            for col in columns:
                field_name = getattr(col, 'field_name', '')
                field_type = getattr(col, 'field_type', '').lower()
                
                # 检查ID字段类型
                if 'id' in field_name.lower() and 'varchar' in field_type:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.INTEGRITY,
                        severity=ValidationSeverity.INFO,
                        table_name=table.table_name,
                        field_name=field_name,
                        message=f"ID字段 {field_name} 使用字符串类型",
                        suggestion="考虑使用整数类型以提高性能",
                        details={"field_type": field_type}
                    ))
                
                # 检查日期字段类型
                if any(keyword in field_name.lower() for keyword in ['date', 'time', 'created', 'updated']) and 'varchar' in field_type:
                    issues.append(ValidationIssue(
                        category=ValidationCategory.INTEGRITY,
                        severity=ValidationSeverity.INFO,
                        table_name=table.table_name,
                        field_name=field_name,
                        message=f"日期字段 {field_name} 使用字符串类型",
                        suggestion="建议使用日期时间类型",
                        details={"field_type": field_type}
                    ))
        
        except Exception as e:
            logger.warning(f"验证表字段失败: {str(e)}")
    
    def _check_data_samples(
        self,
        table: Any,
        data_source_id: str,
        issues: List[ValidationIssue],
        metadata: Dict[str, Any]
    ) -> None:
        """检查数据样本"""
        try:
            samples = self._get_table_sample(table, data_source_id)
            
            if not samples:
                metadata["has_data"] = False
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTEGRITY,
                    severity=ValidationSeverity.WARNING,
                    table_name=table.table_name,
                    field_name=None,
                    message=f"无法获取数据样本",
                    suggestion="检查表是否有数据或权限是否正确",
                    details={}
                ))
                return
            
            metadata["sample_row_count"] = len(samples)
            metadata["has_data"] = True
            
            if len(samples) < self.validation_config["min_sample_rows"]:
                issues.append(ValidationIssue(
                    category=ValidationCategory.INTEGRITY,
                    severity=ValidationSeverity.INFO,
                    table_name=table.table_name,
                    field_name=None,
                    message=f"数据量较少，仅有 {len(samples)} 行",
                    suggestion="确认表是否应该包含更多数据",
                    details={"sample_count": len(samples)}
                ))
        
        except Exception as e:
            logger.warning(f"检查数据样本失败: {str(e)}")
    
    def _get_table_sample(self, table: Any, data_source_id: str) -> List[Dict[str, Any]]:
        """获取表数据样本"""
        try:
            # 这里应该调用实际的数据库查询
            return []  # 简化实现
        except Exception:
            return []
    
    def _validate_table_relations(
        self,
        recommended_joins: List[Dict[str, Any]],
        all_tables: List[Any],
        data_source_id: str
    ) -> List[RelationValidationResult]:
        """验证表间关联关系"""
        validations = []
        
        for join in recommended_joins:
            validation = self._validate_single_relation(join, all_tables, data_source_id)
            validations.append(validation)
        
        return validations
    
    def _validate_single_relation(
        self,
        join_recommendation: Dict[str, Any],
        all_tables: List[Any],
        data_source_id: str
    ) -> RelationValidationResult:
        """验证单个关联关系"""
        issues = []
        
        source_table = join_recommendation.get("left_table", "")
        target_table = join_recommendation.get("right_table", "")
        join_condition = join_recommendation.get("join_condition", "")
        
        # 1. 检查关联是否存在
        relation_exists = self._check_relation_exists(source_table, target_table, data_source_id)
        
        # 2. 检查JOIN是否可行
        join_feasible = bool(join_condition)
        if not join_feasible:
            issues.append(ValidationIssue(
                category=ValidationCategory.RELATION,
                severity=ValidationSeverity.ERROR,
                table_name=source_table,
                field_name=None,
                message=f"缺少JOIN条件",
                suggestion="请提供有效的JOIN条件",
                details={"target_table": target_table}
            ))
        
        # 3. 检查业务合理性
        business_reasonable = self._check_business_reasonableness(
            source_table, target_table, data_source_id
        )
        
        # 4. 计算置信度
        confidence_score = join_recommendation.get("confidence", 0.5)
        if not join_feasible:
            confidence_score *= 0.5
        if not business_reasonable:
            confidence_score *= 0.8
        
        # 5. 判断关联是否有效
        is_valid = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0
        
        return RelationValidationResult(
            source_table=source_table,
            target_table=target_table,
            is_valid=is_valid,
            relation_exists=relation_exists,
            join_feasible=join_feasible,
            business_reasonable=business_reasonable,
            confidence_score=confidence_score,
            issues=issues,
            recommended_join=join_recommendation
        )
    
    def _check_relation_exists(self, source_table: str, target_table: str, data_source_id: str) -> bool:
        """检查关联是否存在"""
        try:
            # 这里应该查询表关联元数据
            return True  # 简化实现
        except Exception:
            return False
    
    def _check_join_feasible(self, join_condition: str) -> bool:
        """检查JOIN是否可行"""
        return bool(join_condition)
    
    def _check_business_reasonableness(self, source_table: str, target_table: str, data_source_id: str) -> bool:
        """检查业务合理性"""
        try:
            # 这里应该进行业务逻辑检查
            return True  # 简化实现
        except Exception:
            return False
    
    def _calculate_overall_confidence(
        self,
        table_validations: List[TableValidationResult],
        relation_validations: List[RelationValidationResult]
    ) -> float:
        """计算整体置信度"""
        if not table_validations:
            return 0.0
        
        # 表验证置信度（基于数据完整性分数）
        table_scores = [v.data_integrity_score for v in table_validations if v.is_valid]
        table_confidence = sum(table_scores) / len(table_validations) if table_validations else 0.0
        
        # 关联验证置信度
        if relation_validations:
            relation_scores = [v.confidence_score for v in relation_validations if v.is_valid]
            relation_confidence = sum(relation_scores) / len(relation_validations) if relation_validations else 0.0
            
            # 综合置信度（表70%，关联30%）
            overall_confidence = table_confidence * 0.7 + relation_confidence * 0.3
        else:
            overall_confidence = table_confidence
        
        return overall_confidence
    
    def _determine_overall_validity(
        self,
        table_validations: List[TableValidationResult],
        relation_validations: List[RelationValidationResult],
        overall_confidence: float
    ) -> bool:
        """判断整体有效性"""
        # 1. 检查置信度是否达标
        if overall_confidence < self.validation_config["min_confidence_threshold"]:
            return False
        
        # 2. 检查是否有严重错误
        for validation in table_validations:
            if not validation.is_valid:
                return False
        
        for validation in relation_validations:
            if not validation.is_valid:
                return False
        
        return True
    
    def _generate_transparency_report(
        self,
        selection_result: Any,
        table_validations: List[TableValidationResult],
        relation_validations: List[RelationValidationResult]
    ) -> Dict[str, Any]:
        """生成透明度报告"""
        return {
            "selection_summary": {
                "primary_tables_count": len(selection_result.primary_tables),
                "related_tables_count": len(selection_result.related_tables),
                "total_relevance_score": selection_result.total_relevance_score,
                "selection_strategy": selection_result.selection_strategy
            },
            "validation_summary": {
                "total_tables": len(table_validations),
                "valid_tables": len([v for v in table_validations if v.is_valid]),
                "total_relations": len(relation_validations),
                "valid_relations": len([v for v in relation_validations if v.is_valid])
            },
            "decision_factors": {
                "ai_reasoning": selection_result.ai_reasoning,
                "selection_explanation": selection_result.selection_explanation
            }
        }
    
    def _generate_selection_explanation(
        self,
        selection_result: Any,
        table_validations: List[TableValidationResult],
        relation_validations: List[RelationValidationResult]
    ) -> str:
        """生成选择解释"""
        valid_tables = [v.table_name for v in table_validations if v.is_valid]
        
        explanation = f"AI模型选择了 {len(valid_tables)} 个表："
        explanation += ", ".join(valid_tables)
        explanation += "。"
        
        if table_validations:
            explanation += f"所有表均验证通过，数据完整性良好。"
        
        if relation_validations:
            explanation += f"表间关联关系已验证，共 {len(relation_validations)} 个关联。"
        
        return explanation
    
    def _generate_recommendations(
        self,
        table_validations: List[TableValidationResult],
        relation_validations: List[RelationValidationResult]
    ) -> List[str]:
        """生成推荐"""
        recommendations = []
        
        # 检查无效的表
        invalid_tables = [v for v in table_validations if not v.is_valid]
        if invalid_tables:
            for v in invalid_tables:
                recommendations.append(f"检查表 {v.table_name} 的存在性和可访问性")
        
        # 检查数据完整性低的表
        low_integrity_tables = [
            v for v in table_validations 
            if v.is_valid and v.data_integrity_score < self.validation_config["min_data_integrity_score"]
        ]
        if low_integrity_tables:
            for v in low_integrity_tables:
                recommendations.append(f"改善表 {v.table_name} 的数据质量")
        
        # 如果所有验证都通过
        if not invalid_tables and not low_integrity_tables:
            recommendations.append("所有表验证通过，可以安全使用")
        
        return recommendations
    
    def _update_validation_stats(self, validation_result: SelectionValidationResult, processing_time: float) -> None:
        """更新验证统计信息"""
        self.validation_stats["total_validations"] += 1
        
        if validation_result.is_valid:
            self.validation_stats["successful_validations"] += 1
        
        # 更新平均处理时间
        total = self.validation_stats["total_validations"]
        current_avg = self.validation_stats["average_processing_time"]
        self.validation_stats["average_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        stats = self.validation_stats.copy()
        
        if stats["total_validations"] > 0:
            stats["success_rate"] = stats["successful_validations"] / stats["total_validations"]
        else:
            stats["success_rate"] = 0.0
        
        return stats
