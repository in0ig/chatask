"""
表关联验证服务单元测试
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from src.models.data_preparation_model import DataTable, TableField, TableRelation
from src.services.relation_validator import RelationValidator

class TestRelationValidator:
    """
    表关联验证服务测试类
    """
    
    @pytest.fixture
    def db_session(self):
        """
        创建模拟的数据库会话
        """
        session = Mock(spec=Session)
        return session
    
    @pytest.fixture
    def validator(self, db_session):
        """
        创建验证器实例
        """
        return RelationValidator(db_session)
    
    def test_validate_field_types_matching(self, validator, db_session):
        """
        测试相同类型字段匹配
        """
        # 创建模拟的主表字段
        primary_field = Mock(spec=TableField)
        primary_field.data_type = "VARCHAR"
        primary_field.id = "primary_field_id"
        
        # 创建模拟的从表字段
        foreign_field = Mock(spec=TableField)
        foreign_field.data_type = "varchar"  # 不同大小写，应该匹配
        foreign_field.id = "foreign_field_id"
        
        # 模拟查询返回
        db_session.query().filter().first.side_effect = [primary_field, foreign_field]
        
        # 执行验证
        result = validator.validate_field_types("primary_field_id", "foreign_field_id")
        
        # 验证结果
        assert result is True
        
    def test_validate_field_types_mismatch(self, validator, db_session):
        """
        测试不同类型字段不匹配
        """
        # 创建模拟的主表字段
        primary_field = Mock(spec=TableField)
        primary_field.data_type = "VARCHAR"
        primary_field.id = "primary_field_id"
        
        # 创建模拟的从表字段
        foreign_field = Mock(spec=TableField)
        foreign_field.data_type = "INTEGER"
        foreign_field.id = "foreign_field_id"
        
        # 模拟查询返回
        db_session.query().filter().first.side_effect = [primary_field, foreign_field]
        
        # 执行验证
        result = validator.validate_field_types("primary_field_id", "foreign_field_id")
        
        # 验证结果
        assert result is False
        
    def test_detect_simple_circular_relation(self, validator, db_session):
        """
        测试简单环路检测 A->B->A
        """
        # 创建模拟的关联
        relation_a_to_b = Mock(spec=TableRelation)
        relation_a_to_b.id = "relation_a_to_b"
        relation_a_to_b.primary_table_id = "table_a"
        relation_a_to_b.foreign_table_id = "table_b"
        
        relation_b_to_a = Mock(spec=TableRelation)
        relation_b_to_a.id = "relation_b_to_a"
        relation_b_to_a.primary_table_id = "table_b"
        relation_b_to_a.foreign_table_id = "table_a"
        
        # 模拟查询返回
        db_session.query().filter().first.side_effect = [relation_a_to_b, relation_b_to_a]
        
        # 模拟查询所有以B为主表的关联
        db_session.query().filter().all.side_effect = [[relation_a_to_b], [relation_b_to_a]]
        
        # 执行检测
        result = validator.detect_circular_relations("relation_a_to_b")
        
        # 验证结果
        assert result is True
        
    def test_detect_complex_circular_relation(self, validator, db_session):
        """
        测试复杂环路检测 A->B->C->A
        """
        # 创建模拟的关联
        relation_a_to_b = Mock(spec=TableRelation)
        relation_a_to_b.id = "relation_a_to_b"
        relation_a_to_b.primary_table_id = "table_a"
        relation_a_to_b.foreign_table_id = "table_b"
        
        relation_b_to_c = Mock(spec=TableRelation)
        relation_b_to_c.id = "relation_b_to_c"
        relation_b_to_c.primary_table_id = "table_b"
        relation_b_to_c.foreign_table_id = "table_c"
        
        relation_c_to_a = Mock(spec=TableRelation)
        relation_c_to_a.id = "relation_c_to_a"
        relation_c_to_a.primary_table_id = "table_c"
        relation_c_to_a.foreign_table_id = "table_a"
        
        # 模拟查询返回
        db_session.query().filter().first.side_effect = [relation_a_to_b, relation_b_to_c, relation_c_to_a]
        
        # 模拟查询所有关联
        db_session.query().filter().all.side_effect = [[relation_a_to_b], [relation_b_to_c], [relation_c_to_a]]
        
        # 执行检测
        result = validator.detect_circular_relations("relation_a_to_b")
        
        # 验证结果
        assert result is True
        
    def test_detect_self_relation(self, validator, db_session):
        """
        测试自关联检测 A->A
        """
        # 创建模拟的自关联
        self_relation = Mock(spec=TableRelation)
        self_relation.id = "self_relation"
        self_relation.primary_table_id = "table_a"
        self_relation.foreign_table_id = "table_a"  # 自关联
        
        # 模拟查询返回
        db_session.query().filter().first.return_value = self_relation
        
        # 执行检测
        result = validator.detect_circular_relations("self_relation")
        
        # 验证结果
        assert result is True
        
    def test_check_relation_dependencies(self, validator, db_session):
        """
        测试关联依赖检查
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "valid_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # 第一次查询：获取关联
        # 第二次查询：获取主表
        # 第三次查询：获取从表
        # 第四次查询：获取主表字段
        # 第五次查询：获取从表字段
        # 第六次查询：再次获取主表字段（检查归属）
        # 第七次查询：再次获取从表字段（检查归属）
        db_session.query().filter().first.side_effect = [
            relation,  # TableRelation 查询
            Mock(),    # DataTable (主表) 查询
            Mock(),    # DataTable (从表) 查询
            Mock(table_id="table_a"),  # TableField (主表字段) 查询
            Mock(table_id="table_b"),  # TableField (从表字段) 查询
            Mock(table_id="table_a"),  # TableField (主表字段) 查询 - 再次检查归属
            Mock(table_id="table_b")   # TableField (从表字段) 查询 - 再次检查归属
        ]
        
        # 执行检查
        issues = validator.check_relation_dependencies("valid_relation")
        
        # 验证结果
        assert len(issues) == 0
        
    def test_check_relation_dependencies_missing_table(self, validator, db_session):
        """
        测试缺失表的依赖检查
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "missing_table_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "nonexistent_table"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # 第一次查询：获取关联
        # 第二次查询：获取主表
        # 第三次查询：获取从表
        # 第四次查询：获取主表字段
        # 第五次查询：获取从表字段
        # 第六次查询：再次获取主表字段（检查归属）
        # 第七次查询：再次获取从表字段（检查归属）
        db_session.query().filter().first.side_effect = [
            relation,  # TableRelation 查询
            Mock(),    # DataTable (主表) 查询
            None,      # DataTable (从表) 查询 - 不存在
            Mock(table_id="table_a"),  # TableField (主表字段) 查询
            Mock(table_id="nonexistent_table"),  # TableField (从表字段) 查询
            Mock(table_id="table_a"),  # TableField (主表字段) 查询 - 再次检查归属
            Mock(table_id="nonexistent_table")   # TableField (从表字段) 查询 - 再次检查归属
        ]
        
        # 执行检查
        issues = validator.check_relation_dependencies("missing_table_relation")
        
        # 验证结果
        assert len(issues) == 1
        assert "从表ID nonexistent_table 不存在" in issues[0]
        
    def test_check_relation_dependencies_missing_field(self, validator, db_session):
        """
        测试缺失字段的依赖检查
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "missing_field_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "nonexistent_field"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # 第一次查询：获取关联
        # 第二次查询：获取主表
        # 第三次查询：获取从表
        # 第四次查询：获取主表字段
        # 第五次查询：获取从表字段
        # 第六次查询：再次获取主表字段（检查归属）
        # 第七次查询：再次获取从表字段（检查归属）
        db_session.query().filter().first.side_effect = [
            relation,  # TableRelation 查询
            Mock(),    # DataTable (主表) 查询
            Mock(),    # DataTable (从表) 查询
            None,      # TableField (主表字段) 查询 - 不存在
            Mock(table_id="table_b"),  # TableField (从表字段) 查询
            None,      # TableField (主表字段) 查询 - 再次检查归属（不存在）
            Mock(table_id="table_b")   # TableField (从表字段) 查询 - 再次检查归属
        ]
        
        # 执行检查
        issues = validator.check_relation_dependencies("missing_field_relation")
        
        # 验证结果
        assert len(issues) == 1
        assert "主表字段ID nonexistent_field 不存在" in issues[0]
        
    def test_validate_relation_full_success(self, validator, db_session):
        """
        测试完整的关联验证成功
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "valid_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        relation.join_type = "INNER"
        
        # 模拟查询返回
        # check_relation_dependencies 需要 7 次查询
        # validate_field_types 需要 2 次查询
        # detect_circular_relations 需要 1 次查询
        # 总共需要 10 次查询
        db_session.query().filter().first.side_effect = [
            relation,  # 1. TableRelation 查询 (check_relation_dependencies)
            Mock(),    # 2. DataTable (主表) 查询 (check_relation_dependencies)
            Mock(),    # 3. DataTable (从表) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 4. TableField (主表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="varchar"),  # 5. TableField (从表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 6. TableField (主表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="varchar"),  # 7. TableField (从表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            relation,  # 8. TableRelation 查询 (validate_relation 获取关联)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 9. TableField (主表字段) 查询 (validate_field_types)
            Mock(table_id="table_b", data_type="varchar"),  # 10. TableField (从表字段) 查询 (validate_field_types)
            relation   # 11. TableRelation 查询 (detect_circular_relations)
        ]
        
        # 模拟查询所有关联（用于环路检测）
        db_session.query().filter().all.side_effect = [[]]
        
        # 执行验证
        result = validator.validate_relation("valid_relation")
        
        # 验证结果
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0
        assert result["field_types_match"] is True
        assert result["circular_relation"] is False
        assert result["dependencies_ok"] is True
        assert len(result["dependency_issues"]) == 0
        
    def test_validate_relation_field_type_mismatch(self, validator, db_session):
        """
        测试关联验证中字段类型不匹配
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "mismatch_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # check_relation_dependencies 需要 7 次查询
        # validate_field_types 需要 2 次查询
        # detect_circular_relations 需要 1 次查询
        # 总共需要 10 次查询
        db_session.query().filter().first.side_effect = [
            relation,  # 1. TableRelation 查询 (check_relation_dependencies)
            Mock(),    # 2. DataTable (主表) 查询 (check_relation_dependencies)
            Mock(),    # 3. DataTable (从表) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 4. TableField (主表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="INTEGER"),  # 5. TableField (从表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 6. TableField (主表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="INTEGER"),  # 7. TableField (从表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            relation,  # 8. TableRelation 查询 (validate_relation 获取关联)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 9. TableField (主表字段) 查询 (validate_field_types)
            Mock(table_id="table_b", data_type="INTEGER"),  # 10. TableField (从表字段) 查询 (validate_field_types)
            relation   # 11. TableRelation 查询 (detect_circular_relations)
        ]
        
        # 模拟查询所有关联（用于环路检测）
        db_session.query().filter().all.side_effect = [[]]
        
        # 执行验证
        result = validator.validate_relation("mismatch_relation")
        
        # 验证结果
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "数据类型不匹配" in result["errors"][0]
        assert result["field_types_match"] is False
        
    def test_validate_relation_circular_dependency(self, validator, db_session):
        """
        测试关联验证中环路依赖
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "circular_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # check_relation_dependencies 需要 7 次查询
        # validate_field_types 需要 2 次查询
        # detect_circular_relations 需要多次查询（递归检测环路）
        # 总共需要更多查询来支持递归环路检测
        db_session.query().filter().first.side_effect = [
            relation,  # 1. TableRelation 查询 (check_relation_dependencies)
            Mock(),    # 2. DataTable (主表) 查询 (check_relation_dependencies)
            Mock(),    # 3. DataTable (从表) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 4. TableField (主表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="VARCHAR"),  # 5. TableField (从表字段) 查询 (check_relation_dependencies)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 6. TableField (主表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            Mock(table_id="table_b", data_type="VARCHAR"),  # 7. TableField (从表字段) 查询 - 再次检查归属 (check_relation_dependencies)
            relation,  # 8. TableRelation 查询 (validate_relation 获取关联)
            Mock(table_id="table_a", data_type="VARCHAR"),  # 9. TableField (主表字段) 查询 (validate_field_types)
            Mock(table_id="table_b", data_type="VARCHAR"),  # 10. TableField (从表字段) 查询 (validate_field_types)
            relation,  # 11. TableRelation 查询 (detect_circular_relations 第一次)
            Mock(id="relation_b_to_a", primary_table_id="table_b", foreign_table_id="table_a"),  # 12. 递归查询子关联
            Mock(id="relation_a_to_b", primary_table_id="table_a", foreign_table_id="table_b")   # 13. 递归查询子关联
        ]
        
        # 模拟查询所有关联（用于环路检测）
        db_session.query().filter().all.side_effect = [
            [Mock(id="relation_b_to_a", primary_table_id="table_b", foreign_table_id="table_a")],  # 第一次查询：获取以table_b为主表的关联
            [Mock(id="relation_a_to_b", primary_table_id="table_a", foreign_table_id="table_b")],  # 第二次查询：获取以table_a为主表的关联
            []  # 第三次查询：没有更多关联
        ]
        
        # 执行验证
        result = validator.validate_relation("circular_relation")
        
        # 验证结果
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "形成环路" in result["errors"][0]
        assert result["circular_relation"] is True
        
    def test_validate_relation_missing_relation(self, validator, db_session):
        """
        测试验证不存在的关联
        """
        # 模拟查询返回
        db_session.query().filter().first.return_value = None
        
        # 执行验证
        result = validator.validate_relation("nonexistent_relation")
        
        # 验证结果
        assert result["is_valid"] is False
        assert len(result["errors"]) == 1
        assert "关联ID nonexistent_relation 不存在" in result["errors"][0]
        
    def test_validate_relation_invalid_field_table_relationship(self, validator, db_session):
        """
        测试字段不属于对应表的验证
        """
        # 创建模拟的关联
        relation = Mock(spec=TableRelation)
        relation.id = "invalid_relationship_relation"
        relation.primary_table_id = "table_a"
        relation.primary_field_id = "field_a"
        relation.foreign_table_id = "table_b"
        relation.foreign_field_id = "field_b"
        
        # 模拟查询返回
        # 第一次调用 check_relation_dependencies 需要 7 次查询
        # 第二次调用 check_relation_dependencies (在 validate_relation 中) 需要 7 次查询
        # validate_field_types 需要 2 次查询
        # detect_circular_relations 需要 1 次查询
        # 总共需要 17 次查询
        db_session.query().filter().first.side_effect = [
            # 第一次调用 check_relation_dependencies
            relation,  # 1. TableRelation 查询
            Mock(),    # 2. DataTable (主表) 查询
            Mock(),    # 3. DataTable (从表) 查询
            Mock(table_id="table_c", data_type="VARCHAR"),  # 4. TableField (主表字段) 查询 - 不属于主表
            Mock(table_id="table_c", data_type="VARCHAR"),  # 5. TableField (从表字段) 查询 - 不属于从表
            Mock(table_id="table_c", data_type="VARCHAR"),  # 6. TableField (主表字段) 查询 - 再次检查归属
            Mock(table_id="table_c", data_type="VARCHAR"),  # 7. TableField (从表字段) 查询 - 再次检查归属
            # 第二次调用 check_relation_dependencies (在 validate_relation 中)
            relation,  # 8. TableRelation 查询
            Mock(),    # 9. DataTable (主表) 查询
            Mock(),    # 10. DataTable (从表) 查询
            Mock(table_id="table_c", data_type="VARCHAR"),  # 11. TableField (主表字段) 查询
            Mock(table_id="table_c", data_type="VARCHAR"),  # 12. TableField (从表字段) 查询
            Mock(table_id="table_c", data_type="VARCHAR"),  # 13. TableField (主表字段) 查询 - 再次检查归属
            Mock(table_id="table_c", data_type="VARCHAR")   # 14. TableField (从表字段) 查询 - 再次检查归属
        ]
        
        # 执行检查
        issues = validator.check_relation_dependencies("invalid_relationship_relation")
        
        # 验证结果
        assert len(issues) == 2
        assert "主表字段ID field_a 不属于主表ID table_a" in issues[0]
        assert "从表字段ID field_b 不属于从表ID table_b" in issues[1]
        
        # 执行验证
        result = validator.validate_relation("invalid_relationship_relation")
        
        # 验证结果
        assert result["is_valid"] is False
        assert len(result["errors"]) == 2
        assert "主表字段ID field_a 不属于主表ID table_a" in result["errors"][0]
        assert "从表字段ID field_b 不属于从表ID table_b" in result["errors"][1]