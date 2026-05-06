import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from src.models.database_models import PromptConfig, PromptType
from src.utils import get_db_session

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PromptService:
    """
    服务类用于管理 Prompt 配置的 CRUD 操作
    """
    
    def __init__(self, db_session: Session):
        """
        初始化 PromptService
        
        Args:
            db_session: SQLAlchemy 数据库会话
        """
        self.db_session = db_session
    
    def create_prompt(self, project_id: str, prompt_type: str, prompt_category: str, 
                     system_prompt: str, user_prompt_template: str, examples: Optional[Dict] = None,
                     temperature: float = 0.7, max_tokens: int = 2048, created_by: str = "system") -> PromptConfig:
        """
        创建新的 Prompt 配置
        
        Args:
            project_id: 项目ID
            prompt_type: Prompt类型（从PromptType枚举中选择）
            prompt_category: Prompt分类
            system_prompt: 系统提示词
            user_prompt_template: 用户提示词模板
            examples: 示例数据，JSON格式
            temperature: 温度参数，默认0.7
            max_tokens: 最大token数，默认2048
            created_by: 创建者
            
        Returns:
            PromptConfig: 创建的Prompt配置对象
            
        Raises:
            ValueError: 参数验证失败
            SQLAlchemyError: 数据库操作失败
        """
        # 参数验证
        if not project_id or not project_id.strip():
            raise ValueError("project_id不能为空")
            
        if not prompt_type or not prompt_type.strip():
            raise ValueError("prompt_type不能为空")
            
        try:
            # 验证prompt_type是否为有效的PromptType枚举值
            if not any(prompt_type == pt.value for pt in PromptType):
                raise ValueError(f"无效的prompt_type: {prompt_type}")
                
        except Exception as e:
            logger.error(f"prompt_type验证失败: {e}")
            raise ValueError(f"无效的prompt_type: {prompt_type}")
            
        if not system_prompt or not system_prompt.strip():
            raise ValueError("system_prompt不能为空")
            
        if not user_prompt_template or not user_prompt_template.strip():
            raise ValueError("user_prompt_template不能为空")
            
        if temperature < 0 or temperature > 2:
            raise ValueError("temperature必须在0-2之间")
            
        if max_tokens <= 0:
            raise ValueError("max_tokens必须大于0")
            
        # 创建Prompt配置
        prompt_config = PromptConfig(
            project_id=project_id,
            prompt_type=PromptType(prompt_type),
            prompt_category=prompt_category,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            examples=examples,
            temperature=temperature,
            max_tokens=max_tokens,
            created_by=created_by
        )
        
        try:
            self.db_session.add(prompt_config)
            self.db_session.commit()
            self.db_session.refresh(prompt_config)
            logger.info(f"成功创建Prompt配置，ID: {prompt_config.id}")
            return prompt_config
            
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"创建Prompt配置失败: {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def get_prompt(self, id: int) -> Optional[PromptConfig]:
        """
        根据ID获取Prompt配置
        
        Args:
            id: Prompt配置ID
            
        Returns:
            PromptConfig: 找到的Prompt配置，未找到返回None
            
        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        try:
            prompt = self.db_session.query(PromptConfig).filter(PromptConfig.id == id).first()
            if prompt:
                logger.info(f"成功获取Prompt配置，ID: {id}")
            else:
                logger.info(f"未找到ID为{id}的Prompt配置")
            return prompt
            
        except SQLAlchemyError as e:
            logger.error(f"获取Prompt配置失败 (ID: {id}): {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def get_prompts(self, project_id: str, prompt_type: Optional[str] = None) -> List[PromptConfig]:
        """
        获取指定项目的所有Prompt配置，可按类型过滤
        
        Args:
            project_id: 项目ID
            prompt_type: 可选的Prompt类型过滤
            
        Returns:
            List[PromptConfig]: Prompt配置列表
            
        Raises:
            ValueError: 项目ID无效
            SQLAlchemyError: 数据库操作失败
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id不能为空")
            
        try:
            query = self.db_session.query(PromptConfig).filter(PromptConfig.project_id == project_id)
            
            if prompt_type:
                # 验证prompt_type是否为有效的PromptType枚举值
                if not any(prompt_type == pt.value for pt in PromptType):
                    raise ValueError(f"无效的prompt_type: {prompt_type}")
                query = query.filter(PromptConfig.prompt_type == PromptType(prompt_type))
                
            prompts = query.order_by(PromptConfig.created_at.desc()).all()
            logger.info(f"成功获取项目{project_id}的{len(prompts)}个Prompt配置")
            return prompts
            
        except SQLAlchemyError as e:
            logger.error(f"获取Prompt配置失败 (项目: {project_id}, 类型: {prompt_type}): {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def get_prompts_by_type(self, project_id: str, prompt_type: str) -> List[PromptConfig]:
        """
        根据项目ID和Prompt类型获取Prompt配置
        
        Args:
            project_id: 项目ID
            prompt_type: Prompt类型
            
        Returns:
            List[PromptConfig]: Prompt配置列表
            
        Raises:
            ValueError: 参数验证失败
            SQLAlchemyError: 数据库操作失败
        """
        if not project_id or not project_id.strip():
            raise ValueError("project_id不能为空")
            
        if not prompt_type or not prompt_type.strip():
            raise ValueError("prompt_type不能为空")
            
        # 验证prompt_type是否为有效的PromptType枚举值
        if not any(prompt_type == pt.value for pt in PromptType):
            raise ValueError(f"无效的prompt_type: {prompt_type}")
            
        try:
            prompts = self.db_session.query(PromptConfig).filter(
                PromptConfig.project_id == project_id,
                PromptConfig.prompt_type == PromptType(prompt_type)
            ).order_by(PromptConfig.created_at.desc()).all()
            
            logger.info(f"成功获取项目{project_id}中类型为{prompt_type}的{len(prompts)}个Prompt配置")
            return prompts
            
        except SQLAlchemyError as e:
            logger.error(f"获取Prompt配置失败 (项目: {project_id}, 类型: {prompt_type}): {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def update_prompt(self, id: int, **kwargs) -> Optional[PromptConfig]:
        """
        更新Prompt配置
        
        Args:
            id: Prompt配置ID
            **kwargs: 要更新的字段
            
        Returns:
            PromptConfig: 更新后的Prompt配置，未找到返回None
            
        Raises:
            ValueError: 参数验证失败
            SQLAlchemyError: 数据库操作失败
        """
        if not id or id <= 0:
            raise ValueError("id必须为正整数")
            
        # 验证允许更新的字段
        allowed_fields = {
            'project_id', 'prompt_type', 'prompt_category', 'system_prompt', 
            'user_prompt_template', 'examples', 'temperature', 'max_tokens', 
            'enabled', 'created_by'
        }
        
        # 过滤无效字段
        valid_kwargs = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not valid_kwargs:
            logger.warning(f"没有提供有效的更新字段，ID: {id}")
            return None
            
        # 如果更新prompt_type，需要验证其有效性
        if 'prompt_type' in valid_kwargs:
            prompt_type_value = valid_kwargs['prompt_type']
            if not prompt_type_value or not prompt_type_value.strip():
                raise ValueError("prompt_type不能为空")
                
            if not any(prompt_type_value == pt.value for pt in PromptType):
                raise ValueError(f"无效的prompt_type: {prompt_type_value}")
                
        try:
            prompt = self.db_session.query(PromptConfig).filter(PromptConfig.id == id).first()
            
            if not prompt:
                logger.info(f"未找到ID为{id}的Prompt配置，无法更新")
                return None
                
            # 更新字段
            for key, value in valid_kwargs.items():
                if key == 'prompt_type':
                    setattr(prompt, key, PromptType(value))
                else:
                    setattr(prompt, key, value)
                    
            self.db_session.commit()
            self.db_session.refresh(prompt)
            logger.info(f"成功更新Prompt配置，ID: {id}")
            return prompt
            
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"更新Prompt配置失败 (ID: {id}): {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def delete_prompt(self, id: int) -> bool:
        """
        删除Prompt配置
        
        Args:
            id: Prompt配置ID
            
        Returns:
            bool: 删除成功返回True，未找到返回False
            
        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        if not id or id <= 0:
            raise ValueError("id必须为正整数")
            
        try:
            prompt = self.db_session.query(PromptConfig).filter(PromptConfig.id == id).first()
            
            if not prompt:
                logger.info(f"未找到ID为{id}的Prompt配置，无法删除")
                return False
                
            self.db_session.delete(prompt)
            self.db_session.commit()
            logger.info(f"成功删除Prompt配置，ID: {id}")
            return True
            
        except SQLAlchemyError as e:
            self.db_session.rollback()
            logger.error(f"删除Prompt配置失败 (ID: {id}): {e}")
            raise SQLAlchemyError(f"数据库操作失败: {str(e)}")
    
    def validate_permission(self, user_id: str, project_id: str, prompt_id: Optional[int] = None) -> bool:
        """
        验证用户是否有权限访问或修改指定的Prompt
        
        Args:
            user_id: 用户ID
            project_id: 项目ID
            prompt_id: Prompt配置ID（可选）
            
        Returns:
            bool: 有权限返回True，无权限返回False
            
        Raises:
            SQLAlchemyError: 数据库操作失败
        """
        # 在实际实现中，这里应该查询用户与项目的关联关系
        # 由于当前模型中没有用户-项目关联表，我们假设用户有权限访问任何项目
        # 在生产环境中，应实现真正的权限验证逻辑
        
        try:
            if prompt_id:
                # 验证Prompt是否存在且属于指定项目
                prompt = self.db_session.query(PromptConfig).filter(
                    PromptConfig.id == prompt_id,
                    PromptConfig.project_id == project_id
                ).first()
                
                if not prompt:
                    logger.warning(f"用户{user_id}尝试访问不存在或不属于项目{project_id}的Prompt {prompt_id}")
                    return False
                
            # 检查用户是否有权限访问项目
            # 在真实环境中，这里应该查询用户与项目的关联关系
            # 由于当前没有用户系统，我们返回True作为占位符
            # 在生产环境中，应实现真正的权限验证逻辑
            logger.info(f"用户{user_id}已通过项目{project_id}的权限验证")
            return True
            
        except SQLAlchemyError as e:
            logger.error(f"权限验证失败 (用户: {user_id}, 项目: {project_id}, Prompt: {prompt_id}): {e}")
            raise SQLAlchemyError(f"权限验证失败: {str(e)}")

# 创建全局服务实例的工厂函数
def get_prompt_service(db_session: Session) -> PromptService:
    """
    获取PromptService实例的工厂函数
    
    Args:
        db_session: SQLAlchemy数据库会话
        
    Returns:
        PromptService: PromptService实例
    """
    return PromptService(db_session)
