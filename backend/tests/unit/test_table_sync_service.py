"""
表结构同步服务单元测试
测试TableSyncService类的所有功能
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from src.models.data_preparation_model import DataTable, TableField
from src.models.data_source_model import DataSource
from src.services.table_sync import TableSyncService


class TestTableSyncService:
    """表结构同步服务测试类"""
    
    def setup_method(self):
        """设置测试环境"""
        self.service = TableSyncService()
        self.db_session = Mock(spec=Session)
        
    @pytest.fixture
    def mock_data_source(self):
        """创建数据源模拟对象"""
        return DataSource(
            id="source-1",
            name="Test MySQL Source",
            source_type="DATABASE",
            db_type="MySQL",
            host="localhost",
            port=3306,
            database_name="test_db",
            username="test_user",
            password="test_pass",
            status=True
        )
    
    @pytest.fixture
    def mock_data_table(self):
        """创建数据表模拟对象"""
        return DataTable(
            id="table-1",
            data_source_id="source-1",
            table_name="test_table",
            display_name="Test Table",
            data_mode="DIRECT_QUERY",
            status=True,
            last_sync_time=None
        )
    
    @pytest.fixture
    def mock_existing_fields(self):
        """创建现有字段模拟列表"""
        return [
            TableField(
                id="field-1",
                table_id="table-1",
                field_name="id",
                data_type="INT",
                is_nullable=False,
                is_primary_key=True,
                description="主键ID"
            ),
            TableField(
                id="field-2",
                table_id="table-1",
                field_name="name",
                data_type="VARCHAR(50)",
                is_nullable=True,
                is_primary_key=False,
                description="姓名"
            ),
            TableField(
                id="field-3",
                table_id="table-1",
                field_name="email",
                data_type="VARCHAR(100)",
                is_nullable=True,
                is_primary_key=False,
                description="邮箱"
            )
        ]
    
    @pytest.fixture
    def mock_existing_fields_postgresql(self):
        """创建PostgreSQL现有字段模拟列表"""
        return [
            TableField(
                id="field-1",
                table_id="table-1",
                field_name="id",
                data_type="integer",
                is_nullable=False,
                is_primary_key=True,
                description="主键ID"
            ),
            TableField(
                id="field-2",
                table_id="table-1",
                field_name="name",
                data_type="character varying(50)",
                is_nullable=True,
                is_primary_key=False,
                description="姓名"
            ),
            TableField(
                id="field-3",
                table_id="table-1",
                field_name="email",
                data_type="character varying(100)",
                is_nullable=True,
                is_primary_key=False,
                description="邮箱"
            )
        ]
    
    def test_sync_mysql_table_structure_success(self, mock_data_source, mock_data_table, mock_existing_fields):
        """测试MySQL表结构同步成功场景"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 模拟数据库查询结果
        mock_db_fields = [
            {"field_name": "id", "data_type": "INT", "is_nullable": False, "is_primary_key": True, "description": "主键ID"},
            {"field_name": "name", "data_type": "VARCHAR(50)", "is_nullable": True, "is_primary_key": False, "description": "姓名"},
            {"field_name": "phone", "data_type": "VARCHAR(20)", "is_nullable": True, "is_primary_key": False, "description": "电话"}
        ]
        
        # 模拟数据库连接和查询
        with patch('src.services.table_sync.create_engine') as mock_create_engine, \
             patch('src.services.table_sync.text') as mock_text:
            
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询结果 - 直接返回元组列表
            mock_connection.execute.return_value = [
                ("id", "INT", "NO", "PRI", "主键ID"),
                ("name", "VARCHAR(50)", "YES", "", "姓名"),
                ("phone", "VARCHAR(20)", "YES", "", "电话")
            ]
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 设置现有字段查询
            self.db_session.query().filter().all.return_value = mock_existing_fields
            
            # 执行同步
            result = self.service.sync_table_structure(self.db_session, "table-1")
            
            # 验证结果
            assert result['created'] == 1  # phone字段被创建
            assert result['updated'] == 0  # 没有字段更新
            assert result['deleted'] == 1  # email字段被删除
            
            # 验证数据库操作
            self.db_session.commit.assert_called_once()
            assert mock_data_table.last_sync_time is not None
            
            # 验证字段操作
            # 验证phone字段被创建
            self.db_session.add.assert_called_once()
            added_field = self.db_session.add.call_args[0][0]
            assert added_field.field_name == "phone"
            assert added_field.data_type == "VARCHAR(20)"
            
            # 验证email字段被删除
            self.db_session.delete.assert_called_once()
            deleted_field = self.db_session.delete.call_args[0][0]
            assert deleted_field.field_name == "email"
    
    def test_sync_postgresql_table_structure_success(self, mock_data_source, mock_data_table, mock_existing_fields_postgresql):
        """测试PostgreSQL表结构同步成功场景"""
        # 设置模拟数据
        mock_data_source.db_type = "PostgreSQL"
        
        # 模拟数据库查询结果
        mock_db_fields = [
            {"field_name": "id", "data_type": "integer", "is_nullable": False, "is_primary_key": True, "description": "主键ID"},
            {"field_name": "name", "data_type": "character varying(50)", "is_nullable": True, "is_primary_key": False, "description": "姓名"},
            {"field_name": "phone", "data_type": "character varying(20)", "is_nullable": True, "is_primary_key": False, "description": "电话"}
        ]
        
        # 模拟数据库连接和查询
        with patch('src.services.table_sync.create_engine') as mock_create_engine, \
             patch('src.services.table_sync.text') as mock_text:
            
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询结果 - 直接返回元组列表
            mock_connection.execute.return_value = [
                ("id", "integer", False, "PRI", "主键ID"),
                ("name", "character varying(50)", True, "", "姓名"),
                ("phone", "character varying(20)", True, "", "电话")
            ]
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 设置现有字段查询
            self.db_session.query().filter().all.return_value = mock_existing_fields_postgresql
            
            # 执行同步
            result = self.service.sync_table_structure(self.db_session, "table-1")
            
            # 验证结果
            assert result['created'] == 1  # phone字段被创建
            assert result['updated'] == 0  # 没有字段更新
            assert result['deleted'] == 1  # email字段被删除
            
            # 验证数据库操作
            self.db_session.commit.assert_called_once()
            assert mock_data_table.last_sync_time is not None
            
            # 验证字段操作
            # 验证phone字段被创建
            self.db_session.add.assert_called_once()
            added_field = self.db_session.add.call_args[0][0]
            assert added_field.field_name == "phone"
            assert added_field.data_type == "character varying(20)"
            
            # 验证email字段被删除
            self.db_session.delete.assert_called_once()
            deleted_field = self.db_session.delete.call_args[0][0]
            assert deleted_field.field_name == "email"
    
    def test_sync_table_source_not_found(self, mock_data_table):
        """测试数据源不存在的场景"""
        # 设置数据库会话的查询行为
        self.db_session.query().filter().first.side_effect = [
            mock_data_table,  # DataTable查询
            None  # DataSource查询失败
        ]
        
        # 验证抛出ValueError异常
        with pytest.raises(ValueError) as exc_info:
            self.service.sync_table_structure(self.db_session, "table-1")
        
        assert "数据源不存在" in str(exc_info.value)
        
        # 验证没有进行数据库提交
        self.db_session.commit.assert_not_called()
    
    def test_sync_table_not_found(self):
        """测试数据表不存在的场景"""
        # 设置数据库会话的查询行为
        self.db_session.query().filter().first.return_value = None
        
        # 验证抛出ValueError异常
        with pytest.raises(ValueError) as exc_info:
            self.service.sync_table_structure(self.db_session, "table-1")
        
        assert "数据表不存在" in str(exc_info.value)
        
        # 验证没有进行数据库提交
        self.db_session.commit.assert_not_called()
    
    def test_sync_database_connection_failed(self, mock_data_source, mock_data_table):
        """测试数据库连接失败的场景"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 模拟数据库连接失败
        with patch('src.services.table_sync.create_engine') as mock_create_engine:
            # 模拟create_engine抛出OperationalError
            mock_engine = Mock()
            mock_engine.connect.side_effect = Exception("Connection failed")
            mock_create_engine.return_value = mock_engine
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 验证抛出异常
            with pytest.raises(Exception) as exc_info:
                self.service.sync_table_structure(self.db_session, "table-1")
            
            assert "Connection failed" in str(exc_info.value)
            
            # 验证没有进行数据库提交
            self.db_session.commit.assert_not_called()
    
    def test_field_info_parsing_accuracy(self, mock_data_source, mock_data_table):
        """测试字段信息解析的准确性"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 模拟数据库查询结果，包含各种边界情况
        mock_db_fields = [
            {"field_name": "id", "data_type": "INT", "is_nullable": False, "is_primary_key": True, "description": "主键ID"},
            {"field_name": "name", "data_type": "VARCHAR(255)", "is_nullable": True, "is_primary_key": False, "description": ""},
            {"field_name": "age", "data_type": "TINYINT", "is_nullable": False, "is_primary_key": False, "description": "年龄"},
            {"field_name": "created_at", "data_type": "DATETIME", "is_nullable": False, "is_primary_key": False, "description": "创建时间"}
        ]
        
        # 模拟数据库连接和查询
        with patch('src.services.table_sync.create_engine') as mock_create_engine, \
             patch('src.services.table_sync.text') as mock_text:
            
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询结果 - 直接返回元组列表
            mock_connection.execute.return_value = [
                ("id", "INT", "NO", "PRI", "主键ID"),
                ("name", "VARCHAR(255)", "YES", "", ""),
                ("age", "TINYINT", "NO", "", "年龄"),
                ("created_at", "DATETIME", "NO", "", "创建时间")
            ]
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 设置现有字段查询 - 返回空列表，表示没有现有字段
            self.db_session.query().filter().all.return_value = []
            
            # 执行同步
            result = self.service.sync_table_structure(self.db_session, "table-1")
            
            # 验证字段信息解析正确
            # 验证添加了4个字段
            assert self.db_session.add.call_count == 4
            
            # 验证第一个添加的字段信息
            first_call = self.db_session.add.call_args_list[0]
            added_field = first_call[0][0]
            assert added_field.field_name == "id"
            assert added_field.data_type == "INT"
            assert added_field.is_nullable == False
            assert added_field.is_primary_key == True
            assert added_field.description == "主键ID"
    
    def test_sync_result_statistics_correctness(self, mock_data_source, mock_data_table):
        """测试同步结果统计的正确性"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 创建现有字段（4个）
        existing_fields = [
            TableField(id="f1", table_id="table-1", field_name="field1", data_type="INT", is_nullable=True, is_primary_key=False, description=""),
            TableField(id="f2", table_id="table-1", field_name="field2", data_type="VARCHAR(50)", is_nullable=False, is_primary_key=False, description=""),
            TableField(id="f3", table_id="table-1", field_name="field3", data_type="TEXT", is_nullable=True, is_primary_key=False, description=""),
            TableField(id="f4", table_id="table-1", field_name="field4", data_type="DATETIME", is_nullable=False, is_primary_key=False, description="")
        ]
        
        # 模拟数据库查询结果（4个字段，其中2个更新，1个新增，1个删除）
        mock_db_fields = [
            {"field_name": "field1", "data_type": "INT", "is_nullable": False, "is_primary_key": False, "description": ""},  # 更新
            {"field_name": "field2", "data_type": "VARCHAR(50)", "is_nullable": False, "is_primary_key": False, "description": ""},  # 无变化
            {"field_name": "field5", "data_type": "VARCHAR(100)", "is_nullable": True, "is_primary_key": False, "description": ""},  # 新增
            {"field_name": "field3", "data_type": "TEXT", "is_nullable": True, "is_primary_key": False, "description": ""}   # 无变化
        ]
        
        # 模拟数据库连接和查询
        with patch('src.services.table_sync.create_engine') as mock_create_engine, \
             patch('src.services.table_sync.text') as mock_text:
            
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询结果 - 直接返回元组列表
            mock_connection.execute.return_value = [
                ("field1", "INT", "NO", "", ""),
                ("field2", "VARCHAR(50)", "NO", "", ""),
                ("field5", "VARCHAR(100)", "YES", "", ""),
                ("field3", "TEXT", "YES", "", "")
            ]
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 设置现有字段查询
            self.db_session.query().filter().all.return_value = existing_fields
            
            # 执行同步
            result = self.service.sync_table_structure(self.db_session, "table-1")
            
            # 验证统计结果
            assert result['created'] == 1  # field5被创建
            assert result['updated'] == 1  # field1被更新（is_nullable从True变为False）
            assert result['deleted'] == 1  # field4被删除
    
    def test_field_create_and_update_logic(self, mock_data_source, mock_data_table):
        """测试字段创建和更新逻辑"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 创建现有字段（1个）
        existing_fields = [
            TableField(id="f1", table_id="table-1", field_name="old_field", data_type="VARCHAR(50)", is_nullable=True, is_primary_key=False, description="旧字段")
        ]
        
        # 模拟数据库查询结果（相同字段但有变化）
        mock_db_fields = [
            {"field_name": "old_field", "data_type": "VARCHAR(100)", "is_nullable": False, "is_primary_key": True, "description": "更新后的字段"}
        ]
        
        # 模拟数据库连接和查询
        with patch('src.services.table_sync.create_engine') as mock_create_engine, \
             patch('src.services.table_sync.text') as mock_text:
            
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询结果 - 直接返回元组列表
            mock_connection.execute.return_value = [
                ("old_field", "VARCHAR(100)", "NO", "PRI", "更新后的字段")
            ]
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 设置现有字段查询
            self.db_session.query().filter().all.return_value = existing_fields
            
            # 执行同步
            result = self.service.sync_table_structure(self.db_session, "table-1")
            
            # 验证统计结果
            assert result['created'] == 0  # 没有新字段创建
            assert result['updated'] == 1  # 1个字段被更新
            assert result['deleted'] == 0  # 没有字段删除
            
            # 验证更新逻辑
            self.db_session.add.assert_not_called()  # 没有添加新字段
            self.db_session.delete.assert_not_called()  # 没有删除字段
            
            # 验证字段更新
            updated_field = existing_fields[0]
            assert updated_field.data_type == "VARCHAR(100)"
            assert updated_field.is_nullable == False
            assert updated_field.is_primary_key == True
            assert updated_field.description == "更新后的字段"
            
            # 验证created=0的逻辑
            # 在同步过程中，如果字段已存在，created应为0
            # 这在上面的assert result['created'] == 0中已经验证
            
            # 验证last_sync_time被更新
            assert mock_data_table.last_sync_time is not None
            
            # 验证commit被调用
            self.db_session.commit.assert_called_once()
    
    def test_sync_with_disabled_source(self, mock_data_source, mock_data_table):
        """测试数据源被禁用时的同步"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        mock_data_source.status = False  # 禁用数据源
        
        # 设置数据库会话的查询行为
        self.db_session.query().filter().first.side_effect = [
            mock_data_table,  # DataTable查询
            mock_data_source  # DataSource查询
        ]
        
        # 验证抛出ValueError异常
        with pytest.raises(ValueError) as exc_info:
            self.service.sync_table_structure(self.db_session, "table-1")
        
        assert "数据源 Test MySQL Source 已禁用" in str(exc_info.value)
        
        # 验证没有进行数据库提交
        self.db_session.commit.assert_not_called()
        
    def test_sync_with_database_error(self, mock_data_source, mock_data_table):
        """测试数据库错误场景"""
        # 设置模拟数据
        mock_data_source.db_type = "MySQL"
        
        # 模拟数据库查询抛出DatabaseError
        with patch('src.services.table_sync.create_engine') as mock_create_engine:
            # 模拟数据库引擎和连接
            mock_engine = Mock()
            mock_connection = Mock()
            mock_connection_context = MagicMock()
            mock_connection_context.__enter__.return_value = mock_connection
            mock_connection_context.__exit__.return_value = None
            mock_engine.connect.return_value = mock_connection_context
            mock_create_engine.return_value = mock_engine
            
            # 模拟查询抛出DatabaseError
            mock_connection.execute.side_effect = Exception("Database error")
            
            # 设置数据库会话的查询行为
            self.db_session.query().filter().first.side_effect = [
                mock_data_table,  # DataTable查询
                mock_data_source  # DataSource查询
            ]
            
            # 验证抛出异常
            with pytest.raises(Exception) as exc_info:
                self.service.sync_table_structure(self.db_session, "table-1")
            
            assert "Database error" in str(exc_info.value)
            
            # 验证没有进行数据库提交
            self.db_session.commit.assert_not_called()
            
    def test_sync_with_unsupported_db_type(self, mock_data_source, mock_data_table):
        """测试不支持的数据库类型"""
        # 设置模拟数据
        mock_data_source.db_type = "Oracle"  # 不支持的数据库类型
        
        # 设置数据库会话的查询行为
        self.db_session.query().filter().first.side_effect = [
            mock_data_table,  # DataTable查询
            mock_data_source  # DataSource查询
        ]
        
        # 验证抛出ValueError异常
        with pytest.raises(ValueError) as exc_info:
            self.service.sync_table_structure(self.db_session, "table-1")
        
        assert "不支持的数据库类型" in str(exc_info.value)
        
        # 验证没有进行数据库提交
        self.db_session.commit.assert_not_called()