import logging
from typing import Dict, Any

# 创建日志记录器
logger = logging.getLogger(__name__)

class SettingsService:
    def __init__(self):
        self.settings = {}
        logger.info("SettingsService initialized")

    def get_settings(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户设置
        """
        logger.debug(f"Retrieving settings for user_id: {user_id}")
        
        settings = self.settings.get(user_id, {})
        logger.info(f"Retrieved {len(settings)} settings for user_id: {user_id}")
        return settings

    def update_settings(self, user_id: str, settings: Dict[str, Any]) -> bool:
        """
        更新用户设置
        """
        logger.info(f"Updating settings for user_id: {user_id}, {len(settings)} settings to update")
        
        if user_id not in self.settings:
            self.settings[user_id] = {}
            logger.debug(f"Created new settings container for user_id: {user_id}")
        
        old_count = len(self.settings[user_id])
        self.settings[user_id].update(settings)
        new_count = len(self.settings[user_id])
        
        logger.info(f"Updated settings for user_id: {user_id}. Changed from {old_count} to {new_count} settings")
        return True

    def delete_settings(self, user_id: str) -> bool:
        """
        删除用户设置
        """
        logger.info(f"Deleting settings for user_id: {user_id}")
        
        if user_id in self.settings:
            old_count = len(self.settings[user_id])
            del self.settings[user_id]
            logger.info(f"Deleted {old_count} settings for user_id: {user_id}")
            return True
        else:
            logger.info(f"No settings found for user_id: {user_id}, nothing to delete")
            return False