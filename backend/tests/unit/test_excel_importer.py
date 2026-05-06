"""
Excel 导入器服务单元测试
测试 ExcelImporter 类的所有功能
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.services.excel_importer import ExcelImporter
import pandas as pd
import os


class TestExcelImporter:
    """Excel 导入器服务测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.db_session = Mock(spec=Session)
        self.importer = ExcelImporter(self.db_session)
    
    @patch('src.services.excel_importer.text')
    @patch('src.services.excel_importer.os.path.exists')
    def test_create_table_from_schema_success(self, mock_exists, mock_text):
        """测试根据表结构创建数据库表成功"""
        # 准备测试数据
        schema = {
            "table_name": "test_table",
            "fields": [
                {"name": "id", "type": "INT", "nullable": False, "primary_key": True},
                {"name": "name", "type": "TEXT", "nullable": True},
                {"name": "age", "type": "INT", "nullable": False, "comment": "用户年龄"}
            ]
        }
        
        # 模拟数据库执行成功
        mock_execute = Mock()
        self.db_session.execute.return_value = mock_execute
        
        # 执行测试
        result = self.importer.create_table_from_schema(schema)
        
        # 验证结果
        assert result is True
        
        # 验证 SQL 语句构建
        expected_sql = "CREATE TABLE `test_table` (`id` INT NOT NULL PRIMARY KEY, `name` TEXT NULL, `age` INT NOT NULL COMMENT '用户年龄')"
        mock_text.assert_called_once_with(expected_sql)
        self.db_session.execute.assert_called_once_with(mock_text.return_value)
        
        # 验证事务提交
        self.db_session.commit.assert_called_once()
        
        # 验证日志
        self.db_session.rollback.assert_not_called()
    
    @patch('src.services.excel_importer.text')
    @patch('src.services.excel_importer.os.path.exists')
    def test_create_table_from_schema_table_exists(self, mock_exists, mock_text):
        """测试创建表时表已存在的情况"""
        # 准备测试数据
        schema = {
            "table_name": "existing_table",
            "fields": [
                {"name": "id", "type": "INT", "nullable": False}
            ]
        }
        
        # 模拟数据库执行失败（表已存在）
        self.db_session.execute.side_effect = Exception("Table 'existing_table' already exists")
        
        # 执行测试
        result = self.importer.create_table_from_schema(schema)
        
        # 验证结果
        assert result is True  # 表已存在视为成功
        
        # 验证 SQL 语句构建
        expected_sql = "CREATE TABLE `existing_table` (`id` INT NOT NULL)"
        self.db_session.execute.assert_called_once_with(mock_text.return_value)
        mock_text.assert_called_once_with(expected_sql)
        
        # 验证事务提交（因为表已存在视为成功，所以应该提交）
        self.db_session.commit.assert_called_once()
        
        # 验证没有回滚
        self.db_session.rollback.assert_not_called()
    
    @patch('src.services.excel_importer.text')
    @patch('src.services.excel_importer.os.path.exists')
    def test_create_table_from_schema_invalid_field_type(self, mock_exists, mock_text):
        """测试创建表时字段类型无效的情况"""
        # 准备测试数据
        schema = {
            "table_name": "invalid_table",
            "fields": [
                {"name": "id", "type": "INVALID_TYPE", "nullable": False}
            ]
        }
        
        # 执行测试
        result = self.importer.create_table_from_schema(schema)
        
        # 验证结果
        assert result is False
        
        # 验证没有执行 SQL
        self.db_session.execute.assert_not_called()
        self.db_session.commit.assert_not_called()
        self.db_session.rollback.assert_not_called()
    
    @patch('src.services.excel_importer.text')
    @patch('src.services.excel_importer.os.path.exists')
    def test_create_table_from_schema_missing_table_name(self, mock_exists, mock_text):
        """测试创建表时缺少表名的情况"""
        # 准备测试数据
        schema = {
            "fields": [
                {"name": "id", "type": "INT", "nullable": False}
            ]
        }
        
        # 执行测试
        result = self.importer.create_table_from_schema(schema)
        
        # 验证结果
        assert result is False
        
        # 验证没有执行 SQL
        self.db_session.execute.assert_not_called()
        self.db_session.commit.assert_not_called()
        self.db_session.rollback.assert_not_called()
    
    @patch('src.services.excel_importer.pd.read_excel')
    @patch('src.services.excel_importer.pd.ExcelFile')
    @patch('src.services.excel_importer.os.path.exists')
    @patch('src.services.excel_importer.text')
    def test_import_excel_data_success(self, mock_text, mock_exists, mock_excel_file, mock_read_excel):
        """测试导入 Excel 数据成功"""
        # 准备测试数据
        file_path = "/test/data.xlsx"
        table_name = "test_table"
        job_id = "job-123"
        
        # 模拟文件存在
        mock_exists.return_value = True
        
        # 模拟 Excel 文件对象和 sheet 名称
        mock_excel_instance = Mock()
        mock_excel_instance.sheet_names = ["Sheet1"]
        mock_excel_file.return_value = mock_excel_instance
        
        # 模拟 Excel 数据
        mock_df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35]
        })
        mock_read_excel.return_value = mock_df
        
        # 模拟数据库执行成功
        mock_execute = Mock()
        self.db_session.execute.return_value = mock_execute
        
        # 执行测试
        result = self.importer.import_excel_data(file_path, table_name, job_id=job_id)
        
        # 验证结果
        assert result["success_count"] == 3
        assert result["failed_count"] == 0
        assert result["total_rows"] == 3
        assert len(result["errors"]) == 0
        
        # 验证文件存在检查
        mock_exists.assert_called_once_with(file_path)
        
        # 验证 Excel 读取
        mock_read_excel.assert_called_once_with(file_path, sheet_name="Sheet1")
        
        # 验证 SQL 执行
        expected_sql = "INSERT INTO `test_table` (`id`, `name`, `age`) VALUES (:id, :name, :age)"
        self.db_session.execute.assert_called_once_with(
            mock_text.return_value,
            [
                {"id": 1, "name": "Alice", "age": 25},
                {"id": 2, "name": "Bob", "age": 30},
                {"id": 3, "name": "Charlie", "age": 35}
            ]
        )
        
        # 验证事务提交
        self.db_session.commit.assert_called_once()
        
        # 验证进度跟踪
        assert job_id in self.importer._job_progress
        progress = self.importer._job_progress[job_id]
        assert progress["status"] == "completed"
        assert progress["progress_percent"] == 100.0
        assert progress["completed_rows"] == 3
        assert progress["total_rows"] == 3
        assert progress["end_time"] is not None
    
    @patch('src.services.excel_importer.pd.read_excel')
    @patch('src.services.excel_importer.pd.ExcelFile')
    @patch('src.services.excel_importer.os.path.exists')
    def test_import_excel_data_invalid_file(self, mock_exists, mock_excel_file, mock_read_excel):
        """测试导入不存在的 Excel 文件"""
        # 准备测试数据
        file_path = "/invalid/data.xlsx"
        table_name = "test_table"
        job_id = "job-456"
        
        # 模拟文件不存在
        mock_exists.return_value = False
        
        # 执行测试
        result = self.importer.import_excel_data(file_path, table_name, job_id=job_id)
        
        # 验证结果
        assert result["success_count"] == 0
        assert result["failed_count"] == 1
        assert result["total_rows"] == 0
        assert len(result["errors"]) == 1
        assert "Excel file not found" in result["errors"][0]
        
        # 验证文件存在检查
        mock_exists.assert_called_once_with(file_path)
        
        # 验证没有尝试读取 Excel
        mock_read_excel.assert_not_called()
        
        # 验证事务没有提交
        self.db_session.execute.assert_not_called()
        self.db_session.commit.assert_not_called()
        
        # 验证进度跟踪
        assert job_id in self.importer._job_progress
        progress = self.importer._job_progress[job_id]
        assert progress["status"] == "failed"
        assert progress["progress_percent"] == 0
        assert progress["completed_rows"] == 0
        assert progress["total_rows"] == 0
        assert progress["end_time"] is not None
        assert isinstance(progress["end_time"], str)  # 确保 end_time 是字符串格式
        assert len(progress["errors"]) == 1
        assert "Excel file not found" in progress["errors"][0]
    
    @patch('src.services.excel_importer.pd.read_excel')
    @patch('src.services.excel_importer.pd.ExcelFile')
    @patch('src.services.excel_importer.os.path.exists')
    def test_import_excel_data_invalid_sheet(self, mock_exists, mock_excel_file, mock_read_excel):
        """测试导入不存在的 sheet"""
        # 准备测试数据
        file_path = "/test/data.xlsx"
        table_name = "test_table"
        sheet_name = "NonExistentSheet"
        job_id = "job-789"
        
        # 模拟文件存在
        mock_exists.return_value = True
        
        # 模拟 Excel 文件没有指定的 sheet
        mock_excel_file = Mock()
        mock_excel_file.sheet_names = ["Sheet1", "Sheet2"]
        
        # 模拟 read_excel 抛出异常
        mock_read_excel.side_effect = ValueError(f"Worksheet named '{sheet_name}' not found")
        
        # 执行测试
        result = self.importer.import_excel_data(file_path, table_name, sheet_name=sheet_name, job_id=job_id)
        
        # 验证结果
        assert result["success_count"] == 0
        assert result["failed_count"] == 1
        assert result["total_rows"] == 0
        assert len(result["errors"]) == 1
        assert "Worksheet named" in result["errors"][0]
        
        # 验证文件存在检查
        mock_exists.assert_called_once_with(file_path)
        
        # 验证 Excel 读取
        mock_read_excel.assert_called_once_with(file_path, sheet_name=sheet_name)
        
        # 验证事务没有提交
        self.db_session.execute.assert_not_called()
        self.db_session.commit.assert_not_called()
        
        # 验证进度跟踪
        assert job_id in self.importer._job_progress
        progress = self.importer._job_progress[job_id]
        assert progress["status"] == "failed"
        assert progress["progress_percent"] == 0
        assert progress["completed_rows"] == 0
        assert progress["total_rows"] == 0
        assert progress["end_time"] is not None
        assert isinstance(progress["end_time"], str)  # 确保 end_time 是字符串格式
        assert len(progress["errors"]) == 1
        assert "Worksheet named" in progress["errors"][0]
    
    @patch('src.services.excel_importer.pd.read_excel')
    @patch('src.services.excel_importer.pd.ExcelFile')
    @patch('src.services.excel_importer.os.path.exists')
    def test_import_excel_data_database_error(self, mock_exists, mock_excel_file, mock_read_excel):
        """测试导入时数据库执行错误"""
        # 准备测试数据
        file_path = "/test/data.xlsx"
        table_name = "test_table"
        job_id = "job-101"
        
        # 模拟文件存在
        mock_exists.return_value = True
        
        # 模拟 Excel 文件对象和 sheet 名称
        mock_excel_instance = Mock()
        mock_excel_instance.sheet_names = ["Sheet1"]
        mock_excel_file.return_value = mock_excel_instance
        
        # 模拟 Excel 数据
        mock_df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"],
            "age": [25, 30, 35]
        })
        mock_read_excel.return_value = mock_df
        
        # 模拟数据库执行失败
        # 由于我们正在模拟 execute 方法，它将在批处理循环中被调用
        self.db_session.execute.side_effect = Exception("Database connection failed")
        
        # 执行测试
        result = self.importer.import_excel_data(file_path, table_name, job_id=job_id)
        
        # 验证结果
        assert result["success_count"] == 0
        assert result["failed_count"] == 3
        assert result["total_rows"] == 3
        assert len(result["errors"]) == 1
        assert "Database connection failed" in result["errors"][0]
        
        # 验证文件存在检查
        mock_exists.assert_called_once_with(file_path)
        
        # 验证 Excel 读取
        mock_read_excel.assert_called_once_with(file_path, sheet_name="Sheet1")
        
        # 验证数据库执行
        self.db_session.execute.assert_called_once()
        
        # 验证事务回滚
        self.db_session.rollback.assert_called_once()
        self.db_session.commit.assert_not_called()
        
        # 验证进度跟踪
        assert job_id in self.importer._job_progress
        progress = self.importer._job_progress[job_id]
        assert progress["status"] == "failed"
        assert progress["progress_percent"] == 0
        assert progress["completed_rows"] == 0
        assert progress["total_rows"] == 3
        assert progress["end_time"] is not None
        assert isinstance(progress["end_time"], str)  # 确保 end_time 是字符串格式
        assert len(progress["errors"]) == 1
        assert "Database connection failed" in progress["errors"][0]
    
    def test_get_import_progress_job_not_found(self):
        """测试获取不存在的导入任务进度"""
        # 执行测试
        result = self.importer.get_import_progress("non-existent-job")
        
        # 验证结果
        assert result["job_id"] == "non-existent-job"
        assert result["status"] == "pending"
        assert result["progress_percent"] == 0
        assert result["completed_rows"] == 0
        assert result["total_rows"] == 0
        assert result["start_time"] is None
        assert result["end_time"] is None
        assert len(result["errors"]) == 0
    
    def test_get_import_progress_job_found(self):
        """测试获取存在的导入任务进度"""
        # 准备测试数据
        job_id = "job-202"
        progress_data = {
            "job_id": job_id,
            "status": "running",
            "progress_percent": 50.0,
            "completed_rows": 50,
            "total_rows": 100,
            "start_time": "2026-01-27T10:00:00",
            "end_time": None,
            "errors": []
        }
        
        # 模拟进度数据
        self.importer._job_progress[job_id] = progress_data
        
        # 执行测试
        result = self.importer.get_import_progress(job_id)
        
        # 验证结果
        assert result == progress_data  # 返回的是副本，但内容应该相同
        assert result is not progress_data  # 确保是副本
    
    def test_get_import_progress_invalid_job_id(self):
        """测试获取导入任务进度时传入无效 job_id"""
        # 测试空字符串
        result = self.importer.get_import_progress("")
        assert result["status"] == "failed"
        assert "job_id is required and cannot be empty" in result["errors"][0]
        
        # 测试 None
        result = self.importer.get_import_progress(None)
        assert result["status"] == "failed"
        assert "job_id is required and cannot be empty" in result["errors"][0]
        
        # 测试非字符串
        result = self.importer.get_import_progress(123)
        assert result["status"] == "failed"
        assert "job_id is required and cannot be empty" in result["errors"][0]
