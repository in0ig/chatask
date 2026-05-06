"""
动态字典服务
负责动态字典的配置管理、SQL查询执行、数据刷新等功能
"""
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from sqlalchemy.exc import SQLAlchemyError

from ..models.data_preparation_model import DynamicDictionaryConfig, Dictionary, DictionaryItem
from ..models.data_source_model import DataSource
from ..schemas.dynamic_dictionary_schema import (
    DynamicDictionaryConfigCreate,
    DynamicDictionaryConfigUpdate,
    QueryTestRequest,
    QueryTestResponse,
    RefreshResult
)
from ..utils.encryption import decrypt_password

logger = logging.getLogger(__name__)


class DynamicDictionaryService:
    """动态字典服务类"""

    def __init__(self, db: Session):
        self.db = db

    def create_config(self, config_data: DynamicDictionaryConfigCreate) -> DynamicDictionaryConfig:
        """创建动态字典配置"""
        try:
            # 检查字典是否存在
            dictionary = self.db.query(Dictionary).filter(
                Dictionary.id == config_data.dictionary_id
            ).first()
            if not dictionary:
                raise ValueError(f"字典 {config_data.dictionary_id} 不存在")

            # 检查数据源是否存在
            data_source = self.db.query(DataSource).filter(
                DataSource.id == config_data.data_source_id
            ).first()
            if not data_source:
                raise ValueError(f"数据源 {config_data.data_source_id} 不存在")

            # 检查是否已存在配置
            existing_config = self.db.query(DynamicDictionaryConfig).filter(
                DynamicDictionaryConfig.dictionary_id == config_data.dictionary_id
            ).first()
            if existing_config:
                raise ValueError(f"字典 {config_data.dictionary_id} 已存在动态配置")

            # 创建配置
            config = DynamicDictionaryConfig(
                dictionary_id=config_data.dictionary_id,
                data_source_id=config_data.data_source_id,
                sql_query=config_data.sql_query,
                key_field=config_data.key_field,
                value_field=config_data.value_field,
                refresh_interval=config_data.refresh_interval
            )

            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)

            logger.info(f"创建动态字典配置成功: {config.id}")
            return config

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建动态字典配置失败: {str(e)}")
            raise

    def get_config(self, dictionary_id: str) -> Optional[DynamicDictionaryConfig]:
        """获取动态字典配置"""
        return self.db.query(DynamicDictionaryConfig).filter(
            DynamicDictionaryConfig.dictionary_id == dictionary_id
        ).first()

    def update_config(self, dictionary_id: str, config_data: DynamicDictionaryConfigUpdate) -> DynamicDictionaryConfig:
        """更新动态字典配置"""
        try:
            config = self.get_config(dictionary_id)
            if not config:
                raise ValueError(f"字典 {dictionary_id} 的动态配置不存在")

            # 更新字段
            update_data = config_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(config, field, value)

            self.db.commit()
            self.db.refresh(config)

            logger.info(f"更新动态字典配置成功: {config.id}")
            return config

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新动态字典配置失败: {str(e)}")
            raise

    def delete_config(self, dictionary_id: str) -> bool:
        """删除动态字典配置"""
        try:
            config = self.get_config(dictionary_id)
            if not config:
                raise ValueError(f"字典 {dictionary_id} 的动态配置不存在")

            self.db.delete(config)
            self.db.commit()

            logger.info(f"删除动态字典配置成功: {config.id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除动态字典配置失败: {str(e)}")
            raise

    def test_query(self, test_request: QueryTestRequest) -> QueryTestResponse:
        """测试SQL查询"""
        start_time = time.time()
        
        try:
            # 获取数据源
            data_source = self.db.query(DataSource).filter(
                DataSource.id == test_request.data_source_id
            ).first()
            if not data_source:
                return QueryTestResponse(
                    success=False,
                    message=f"数据源 {test_request.data_source_id} 不存在"
                )

            # 创建数据库连接
            engine = self._create_engine(data_source)
            
            # 执行查询
            with engine.connect() as conn:
                # 先执行计数查询
                count_query = f"SELECT COUNT(*) as total FROM ({test_request.sql_query}) as subquery"
                count_result = conn.execute(text(count_query))
                total_count = count_result.fetchone()[0]

                # 执行限制查询获取示例数据
                limited_query = f"SELECT {test_request.key_field}, {test_request.value_field} FROM ({test_request.sql_query}) as subquery LIMIT 10"
                result = conn.execute(text(limited_query))
                
                sample_data = []
                for row in result:
                    sample_data.append({
                        test_request.key_field: row[0],
                        test_request.value_field: row[1]
                    })

            execution_time = int((time.time() - start_time) * 1000)

            return QueryTestResponse(
                success=True,
                message="查询执行成功",
                sample_data=sample_data,
                total_count=total_count,
                execution_time_ms=execution_time
            )

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"测试SQL查询失败: {str(e)}")
            return QueryTestResponse(
                success=False,
                message=f"查询执行失败: {str(e)}",
                execution_time_ms=execution_time
            )

    def refresh_dictionary(self, dictionary_id: str) -> RefreshResult:
        """刷新动态字典数据"""
        start_time = time.time()
        
        try:
            # 获取配置
            config = self.get_config(dictionary_id)
            if not config:
                raise ValueError(f"字典 {dictionary_id} 的动态配置不存在")

            # 获取数据源
            data_source = self.db.query(DataSource).filter(
                DataSource.id == config.data_source_id
            ).first()
            if not data_source:
                raise ValueError(f"数据源 {config.data_source_id} 不存在")

            # 执行查询获取新数据
            engine = self._create_engine(data_source)
            new_items = {}
            
            with engine.connect() as conn:
                query = f"SELECT {config.key_field}, {config.value_field} FROM ({config.sql_query}) as subquery"
                result = conn.execute(text(query))
                
                for row in result:
                    key = str(row[0]) if row[0] is not None else ""
                    value = str(row[1]) if row[1] is not None else ""
                    new_items[key] = value

            # 获取现有字典项
            existing_items = self.db.query(DictionaryItem).filter(
                DictionaryItem.dictionary_id == dictionary_id
            ).all()
            
            existing_keys = {item.item_key: item for item in existing_items}

            # 统计变更
            items_added = 0
            items_updated = 0
            items_removed = 0

            # 添加或更新字典项
            for key, value in new_items.items():
                if key in existing_keys:
                    # 更新现有项
                    if existing_keys[key].item_value != value:
                        existing_keys[key].item_value = value
                        items_updated += 1
                else:
                    # 添加新项
                    new_item = DictionaryItem(
                        dictionary_id=dictionary_id,
                        item_key=key,
                        item_value=value,
                        status=True
                    )
                    self.db.add(new_item)
                    items_added += 1

            # 删除不存在的项
            for key, item in existing_keys.items():
                if key not in new_items:
                    self.db.delete(item)
                    items_removed += 1

            # 更新最后刷新时间
            config.last_refresh_time = datetime.utcnow()
            
            self.db.commit()

            execution_time = int((time.time() - start_time) * 1000)

            result = RefreshResult(
                success=True,
                message="字典刷新成功",
                items_added=items_added,
                items_updated=items_updated,
                items_removed=items_removed,
                total_items=len(new_items),
                refresh_time=config.last_refresh_time,
                execution_time_ms=execution_time
            )

            logger.info(f"刷新动态字典成功: {dictionary_id}, 新增: {items_added}, 更新: {items_updated}, 删除: {items_removed}")
            return result

        except Exception as e:
            self.db.rollback()
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"刷新动态字典失败: {str(e)}")
            return RefreshResult(
                success=False,
                message=f"刷新失败: {str(e)}",
                refresh_time=datetime.utcnow(),
                execution_time_ms=execution_time
            )

    def get_configs_list(self, page: int = 1, page_size: int = 20) -> Tuple[List[DynamicDictionaryConfig], int]:
        """获取动态字典配置列表"""
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 查询总数
            total = self.db.query(DynamicDictionaryConfig).count()

            # 查询配置列表
            configs = self.db.query(DynamicDictionaryConfig)\
                .offset(offset)\
                .limit(page_size)\
                .all()

            return configs, total

        except Exception as e:
            logger.error(f"获取动态字典配置列表失败: {str(e)}")
            raise

    def _create_engine(self, data_source: DataSource):
        """创建数据库引擎"""
        try:
            # 解密密码
            password = decrypt_password(data_source.password) if data_source.password else ""
            
            # 构建连接字符串
            if data_source.db_type == "MySQL":
                connection_string = f"mysql+pymysql://{data_source.username}:{password}@{data_source.host}:{data_source.port}/{data_source.database_name}"
            elif data_source.db_type == "PostgreSQL":
                connection_string = f"postgresql://{data_source.username}:{password}@{data_source.host}:{data_source.port}/{data_source.database_name}"
            elif data_source.db_type == "SQLServer":
                connection_string = f"mssql+pyodbc://{data_source.username}:{password}@{data_source.host}:{data_source.port}/{data_source.database_name}?driver=ODBC+Driver+17+for+SQL+Server"
            else:
                raise ValueError(f"不支持的数据库类型: {data_source.db_type}")

            # 创建引擎
            engine = create_engine(
                connection_string,
                pool_timeout=30,
                pool_recycle=3600
            )
            
            return engine

        except Exception as e:
            logger.error(f"创建数据库引擎失败: {str(e)}")
            raise

    def check_refresh_needed(self, dictionary_id: str) -> bool:
        """检查是否需要刷新"""
        try:
            config = self.get_config(dictionary_id)
            if not config:
                return False

            if not config.last_refresh_time:
                return True

            # 计算时间差
            time_diff = datetime.utcnow() - config.last_refresh_time
            return time_diff.total_seconds() >= config.refresh_interval

        except Exception as e:
            logger.error(f"检查刷新需求失败: {str(e)}")
            return False