"""
异步表结构同步服务
实现异步执行、任务状态管理和进度通知
"""
import logging
import uuid
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
from fastapi import BackgroundTasks

# 任务状态枚举
class SyncTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# 任务状态存储（内存中，生产环境应使用数据库）
class SyncTaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
    
    def create_task(self, table_id: str) -> str:
        """创建新任务并返回任务ID"""
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "table_id": table_id,
            "status": SyncTaskStatus.PENDING,
            "progress": 0,
            "started_at": datetime.now(),
            "ended_at": None,
            "result": None,
            "error": None,
            "cancelled": False
        }
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
    
    def cancel_task(self, task_id: str):
        """取消任务"""
        if task_id in self.tasks:
            self.tasks[task_id]["cancelled"] = True
            self.tasks[task_id]["status"] = SyncTaskStatus.CANCELLED
            self.tasks[task_id]["ended_at"] = datetime.now()
    
    def delete_task(self, task_id: str):
        """删除任务（用于清理已完成任务）"""
        if task_id in self.tasks:
            del self.tasks[task_id]

# 创建任务管理器实例
task_manager = SyncTaskManager()

# 异步同步任务函数
def async_table_sync_task(task_id: str, table_id: str):
    """异步表结构同步任务主体"""
    from src.services.table_sync import sync_service
    from src.database import get_db
    
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 更新任务状态为运行中
        task_manager.update_task(task_id, status=SyncTaskStatus.RUNNING, progress=10)
        
        # 获取数据表信息
        table = db.query(DataTable).filter(DataTable.id == table_id).first()
        if not table:
            raise ValueError(f"数据表不存在: {table_id}")
        
        # 获取数据源信息
        source = db.query(DataSource).filter(DataSource.id == table.data_source_id).first()
        if not source:
            raise ValueError(f"数据源不存在: {table.data_source_id}")
        
        # 构建连接字符串
        connection_string = sync_service._build_connection_string(source)
        
        # 创建数据库引擎
        engine = create_engine(connection_string)
        
        # 连接数据库并获取表结构
        with engine.connect() as connection:
            # 获取表结构信息
            table_structure = sync_service._get_table_structure(connection, source.db_type, table.table_name)
            
            # 获取当前系统中的字段
            existing_fields = db.query(TableField).filter(TableField.table_id == table_id).all()
            existing_fields_map = {field.field_name: field for field in existing_fields}
            
            # 同步字段 - 分阶段进行以支持进度更新
            total_steps = len(table_structure) + len(existing_fields_map) + 2  # 新增字段 + 删除字段 + 更新表信息
            current_step = 0
            
            # 处理新字段和更新字段
            created_count = 0
            updated_count = 0
            deleted_count = 0
            
            # 阶段1: 处理新字段和更新字段
            for field_info in table_structure:
                if task_manager.get_task(task_id)["cancelled"]:
                    break
                
                field_name = field_info['field_name']
                
                if field_name in existing_fields_map:
                    # 更新现有字段
                    field = existing_fields_map[field_name]
                    if sync_service._field_has_changed(field, field_info):
                        sync_service._update_field(db, field, field_info)
                        updated_count += 1
                    del existing_fields_map[field_name]
                else:
                    # 创建新字段
                    sync_service._create_field(db, table_id, field_info)
                    created_count += 1
                
                # 更新进度
                current_step += 1
                progress = min(100, int((current_step / total_steps) * 80) + 10)  # 10-90% 用于字段处理
                task_manager.update_task(task_id, progress=progress)
                
            # 阶段2: 删除不再存在的字段
            for field_name, field in existing_fields_map.items():
                if task_manager.get_task(task_id)["cancelled"]:
                    break
                
                db.delete(field)
                deleted_count += 1
                
                # 更新进度
                current_step += 1
                progress = min(100, int((current_step / total_steps) * 80) + 10)
                task_manager.update_task(task_id, progress=progress)
                
            # 阶段3: 更新表的最后同步时间
            if not task_manager.get_task(task_id)["cancelled"]:
                table.last_sync_time = datetime.now()
                db.commit()
                
                # 更新进度到100%
                task_manager.update_task(task_id, progress=100)
                
                # 记录结果
                result = {
                    'created': created_count,
                    'updated': updated_count,
                    'deleted': deleted_count
                }
                task_manager.update_task(task_id, status=SyncTaskStatus.COMPLETED, result=result)
                
    except Exception as e:
        # 记录错误信息
        error_msg = str(e)
        task_manager.update_task(task_id, status=SyncTaskStatus.FAILED, error=error_msg)
        
        # 回滚数据库
        try:
            db.rollback()
        except:
            pass
        
        logging.error(f"异步表结构同步任务失败 (task_id: {task_id}): {error_msg}")
    
    finally:
        # 关闭数据库会话
        try:
            db.close()
        except:
            pass
        
        # 如果任务被取消，确保状态正确
        if task_manager.get_task(task_id)["cancelled"] and task_manager.get_task(task_id)["status"] != SyncTaskStatus.FAILED:
            task_manager.update_task(task_id, status=SyncTaskStatus.CANCELLED)
        
        # 设置结束时间
        task_manager.update_task(task_id, ended_at=datetime.now())

# 导出任务管理器
__all__ = ["task_manager", "async_table_sync_task", "SyncTaskStatus"]
