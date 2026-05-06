import logging
import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional

# 创建日志记录器
logger = logging.getLogger(__name__)

class ExcelImporter:
    """
    Excel 导入器，负责将 Excel 文件数据导入数据库
    """
    
    def __init__(self, db_session: Session):
        """
        初始化 Excel 导入器
        
        Args:
            db_session (Session): SQLAlchemy 数据库会话
        """
        self.db_session = db_session
        logger.info("ExcelImporter initialized with database session")
    
    def create_table_from_schema(self, schema: Dict[str, Any]) -> bool:
        """
        根据表结构创建数据库表
        
        Args:
            schema (Dict[str, Any]): 包含表名、字段定义等信息的结构
                - table_name (str): 表名
                - fields (List[Dict[str, str]]): 字段定义列表，每个字段包含:
                    - name (str): 字段名
                    - type (str): 字段类型 (TEXT, INT, DECIMAL, DATETIME)
                    - nullable (bool, optional): 是否允许为空，默认为 True
                    - primary_key (bool, optional): 是否为主键，默认为 False
                    - comment (str, optional): 字段注释
            
        Returns:
            bool: 创建成功返回 True，失败返回 False
        """
        table_name = schema.get("table_name")
        fields = schema.get("fields", [])
        
        if not table_name:
            logger.error("Table name is required in schema")
            return False
        
        if not fields:
            logger.warning(f"No fields specified for table {table_name}")
        
        try:
            # 构建 CREATE TABLE 语句
            columns = []
            
            # 映射字段类型到 MySQL 数据类型
            type_mapping = {
                "TEXT": "TEXT",
                "INT": "INT",
                "DECIMAL": "DECIMAL",
                "DATETIME": "DATETIME"
            }
            
            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type", "TEXT").upper()
                nullable = field.get("nullable", True)
                primary_key = field.get("primary_key", False)
                comment = field.get("comment", "")
                
                if not field_name:
                    logger.error(f"Field name is required for table {table_name}")
                    return False
                
                # 验证字段类型
                if field_type not in type_mapping:
                    logger.error(f"Unsupported field type '{field_type}' for field '{field_name}' in table {table_name}")
                    return False
                
                # 构建列定义
                column_def = f"`{field_name}` {type_mapping[field_type]}"
                
                # 添加是否允许为空
                if not nullable:
                    column_def += " NOT NULL"
                else:
                    column_def += " NULL"
                
                # 添加主键约束
                if primary_key:
                    column_def += " PRIMARY KEY"
                
                # 添加注释
                if comment:
                    column_def += f" COMMENT '{comment.replace('"', '\"')}'"
                
                columns.append(column_def)
            
            # 构建完整的 CREATE TABLE 语句
            if columns:
                columns_str = ", ".join(columns)
                create_table_sql = f"CREATE TABLE `{table_name}` ({columns_str})"
            else:
                # 如果没有字段，创建一个空表（仅包含主键）
                create_table_sql = f"CREATE TABLE `{table_name}` (id INT PRIMARY KEY)"
            
            logger.info(f"Executing CREATE TABLE SQL for {table_name}: {create_table_sql}")
            
            # 执行 SQL 语句
            self.db_session.execute(text(create_table_sql))
            self.db_session.commit()
            
            logger.info(f"Successfully created table {table_name}")
            return True
            
        except Exception as e:
            # 捕获表已存在等错误
            error_msg = str(e)
            logger.error(f"Failed to create table {table_name}: {error_msg}")
            
            # 特别处理表已存在的错误
            if "already exists" in error_msg.lower() or "table" in error_msg.lower() and "exists" in error_msg.lower():
                logger.warning(f"Table {table_name} already exists, skipping creation")
                self.db_session.commit()  # 表已存在视为成功，提交事务
                return True
            
            # 回滚事务
            self.db_session.rollback()
            return False
    
    def import_excel_data(self, file_path: str, table_name: str, sheet_name: Optional[str] = None, job_id: Optional[str] = None) -> Dict[str, Any]:
        """
        导入 Excel 文件数据到指定数据库表
        
        Args:
            file_path (str): Excel 文件路径
            table_name (str): 目标数据库表名
            sheet_name (Optional[str]): 指定要导入的 sheet 名称，如果为 None 则导入第一个 sheet
            job_id (Optional[str]): 导入任务的唯一标识符，用于进度跟踪
            
        Returns:
            Dict[str, Any]: 导入结果，包含成功行数、错误信息等
        """
        logger.info(f"Importing Excel data from {file_path} to table {table_name}, sheet: {sheet_name}, job_id: {job_id}")
        
        result = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "total_rows": 0
        }
        
        try:
            # 验证文件是否存在
            if not os.path.exists(file_path):
                error_msg = f"Excel file not found: {file_path}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                result["failed_count"] = 1
                
                # 如果提供了 job_id，更新进度状态
                if job_id:
                    current_time = pd.Timestamp.now().isoformat()
                    self._job_progress[job_id] = {
                        "job_id": job_id,
                        "status": "failed",
                        "progress_percent": 0,
                        "completed_rows": 0,
                        "total_rows": 0,
                        "start_time": current_time,
                        "end_time": current_time,
                        "errors": [error_msg]
                    }
                
                return result
            
            # 读取 Excel 文件
            logger.info(f"Reading Excel file: {file_path}")
            
            # 如果没有指定 sheet_name，则读取第一个 sheet
            if sheet_name is None:
                # 获取所有 sheet 名称
                excel_file = pd.ExcelFile(file_path)
                if not excel_file.sheet_names:
                    error_msg = f"No sheets found in Excel file: {file_path}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["failed_count"] = 1
                    
                    # 如果提供了 job_id，更新进度状态
                    if job_id:
                        self._job_progress[job_id] = {
                            "job_id": job_id,
                            "status": "failed",
                            "progress_percent": 0,
                            "completed_rows": 0,
                            "total_rows": 0,
                            "start_time": None,
                            "end_time": None,
                            "errors": [error_msg]
                        }
                    
                    return result
                sheet_name = excel_file.sheet_names[0]
                logger.info(f"Using first sheet: {sheet_name}")
            
            # 如果提供了 job_id，初始化进度信息
            if job_id:
                self._job_progress[job_id] = {
                    "job_id": job_id,
                    "status": "running",
                    "progress_percent": 0,
                    "completed_rows": 0,
                    "total_rows": 0,  # 暂时设为0，因为还没有读取数据
                    "start_time": pd.Timestamp.now().isoformat(),
                    "end_time": None,
                    "errors": []
                }
            
            # 读取指定 sheet 的数据
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            except Exception as e:
                error_msg = f"Failed to read Excel file: {str(e)}"
                logger.error(error_msg)
                result["errors"].append(error_msg)
                result["failed_count"] = 1  # 一个独立的错误
                
                # 如果提供了 job_id，更新为失败状态
                if job_id:
                    self._job_progress[job_id] = {
                        "job_id": job_id,
                        "status": "failed",
                        "progress_percent": 0,
                        "completed_rows": 0,
                        "total_rows": 0,
                        "start_time": pd.Timestamp.now().isoformat(),
                        "end_time": pd.Timestamp.now().isoformat(),
                        "errors": [error_msg]
                    }
                
                return result
            
            # 记录总行数
            result["total_rows"] = len(df)
            logger.info(f"Successfully read {len(df)} rows from sheet '{sheet_name}'")
            
            # 处理空值：将 NaN 转换为 None
            df = df.where(pd.notnull(df), None)
            
            # 将 DataFrame 转换为字典列表
            data_records = df.to_dict('records')
            
            # 更新 total_rows
            if job_id:
                self._job_progress[job_id]["total_rows"] = len(data_records)
            
            # 分批处理，每批 1000 条记录
            batch_size = 1000
            total_batches = (len(data_records) + batch_size - 1) // batch_size
            
            logger.info(f"Processing {len(data_records)} records in {total_batches} batches of {batch_size} records each")
            
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, len(data_records))
                batch_data = data_records[start_idx:end_idx]
                
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches}: {len(batch_data)} records")
                
                try:
                    # 使用 SQLAlchemy bulk_insert_mappings 进行批量插入
                    # 注意：bulk_insert_mappings 需要映射到模型类，但这里我们直接使用原始数据
                    # 因为没有具体的模型类，我们将使用原始字典数据进行插入
                    # 这需要数据库表结构与 Excel 列名匹配
                    
                    # 构建插入语句
                    # 使用原始字典数据，假设列名与数据库字段名匹配
                    
                    # 执行批量插入
                    self.db_session.execute(
                        text(f"INSERT INTO `{table_name}` ({', '.join([f'`{col}`' for col in df.columns])}) "
                             f"VALUES ({', '.join([f':{col}' for col in df.columns])})"),
                        batch_data
                    )
                    
                    # 更新成功计数
                    result["success_count"] += len(batch_data)
                    
                    logger.info(f"Successfully inserted {len(batch_data)} records in batch {batch_idx + 1}")
                    
                    # 如果提供了 job_id，更新进度信息
                    if job_id:
                        completed_rows = result["success_count"]
                        progress_percent = (completed_rows / len(data_records)) * 100 if len(data_records) > 0 else 0
                        
                        self._job_progress[job_id].update({
                            "completed_rows": completed_rows,
                            "progress_percent": round(progress_percent, 2),
                            "errors": self._job_progress[job_id]["errors"]  # 保持错误列表
                        })
                        
                except Exception as batch_error:
                    error_msg = f"Batch {batch_idx + 1} failed: {str(batch_error)}"
                    logger.error(error_msg)
                    result["errors"].append(error_msg)
                    result["failed_count"] += len(batch_data)
                    
                    # 如果提供了 job_id，更新错误信息
                    if job_id:
                        self._job_progress[job_id]["errors"].append(error_msg)
                    
                    # 如果是数据库连接失败等严重错误，停止处理并触发最外层异常
                    if "connection" in str(batch_error).lower() or "database" in str(batch_error).lower():
                        raise
                    
                    # 否则继续处理其他批次
                    continue
            
            # 提交事务
            self.db_session.commit()
            logger.info(f"Excel data import completed successfully: {result['success_count']} rows inserted, {result['failed_count']} rows failed")
            
            # 如果提供了 job_id，更新为完成状态
            if job_id:
                self._job_progress[job_id].update({
                    "status": "completed",
                    "end_time": pd.Timestamp.now().isoformat()
                })
                
        except Exception as e:
            # 发生异常时回滚事务
            self.db_session.rollback()
            error_msg = f"Failed to import Excel data: {str(e)}"
            logger.error(error_msg)
            # 不重复添加错误，因为错误已经在批处理循环中添加
            # result["errors"].append(error_msg)
            # 当发生异常时，所有行都失败
            result["failed_count"] = result["total_rows"]
            
            # 如果提供了 job_id，更新为失败状态
            if job_id:
                self._job_progress[job_id].update({
                    "status": "failed",
                    "end_time": pd.Timestamp.now().isoformat(),
                    "errors": self._job_progress[job_id].get("errors", [])
                })
                
        return result
    
    # Class-level dictionary to store import job progress information
    _job_progress = {}
    
    def cancel_job(self, job_id: str) -> bool:
        """
        取消正在进行的 Excel 导入任务
        
        Args:
            job_id (str): 要取消的导入任务的唯一标识符
            
        Returns:
            bool: 如果任务成功取消返回 True，如果任务不存在或无法取消返回 False
        """
        logger.info(f"Attempting to cancel job: {job_id}")
        
        # 检查 job_id 是否存在于 _job_progress 中
        if job_id not in self._job_progress:
            logger.warning(f"Job {job_id} not found, cannot cancel")
            return False
        
        # 获取当前任务状态
        job_info = self._job_progress[job_id]
        current_status = job_info.get("status", "")
        
        # 只有当任务状态为 'pending' 或 'running' 时才能取消
        if current_status not in ["pending", "running"]:
            logger.info(f"Job {job_id} is in status '{current_status}', cannot be cancelled")
            return False
        
        # 更新任务状态为 'cancelled'
        job_info["status"] = "cancelled"
        
        # 设置结束时间为当前时间
        current_time = pd.Timestamp.now().isoformat()
        job_info["end_time"] = current_time
        
        # 添加取消消息到 errors 列表
        cancel_message = f"Job cancelled by user request at {current_time}"
        job_info["errors"].append(cancel_message)
        
        logger.info(f"Successfully cancelled job {job_id}")
        return True
    
    def get_import_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取导入任务的进度状态
        
        Args:
            job_id (str): 导入任务的唯一标识符
            
        Returns:
            Dict[str, Any] | None: 包含导入进度、已完成行数、总行数、状态等信息
            - job_id: 任务ID
            - status: 'pending', 'running', 'completed', 'failed'
            - progress_percent: 进度百分比 (0-100)
            - completed_rows: 已完成的行数
            - total_rows: 总行数
            - start_time: 任务开始时间
            - end_time: 任务结束时间
            - errors: 错误列表
            如果任务不存在，返回 None
        """
        # 参数验证
        if not job_id or not isinstance(job_id, str) or not job_id.strip():
            logger.error("get_import_progress: job_id is required and cannot be empty")
            return {
                "job_id": job_id,
                "status": "failed",
                "progress_percent": 0,
                "completed_rows": 0,
                "total_rows": 0,
                "start_time": None,
                "end_time": None,
                "errors": ["job_id is required and cannot be empty"]
            }
        
        logger.info(f"Getting import progress for job: {job_id}")
        
        # 如果任务不存在，返回 None
        if job_id not in self._job_progress:
            logger.info(f"Job {job_id} not found, returning None")
            return None
        
        # 返回任务进度信息的副本
        return self._job_progress[job_id].copy()
