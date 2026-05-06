import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from src.models.settings_model import UserSettings
from src.services.settings_service import SettingsService

# 创建日志记录器
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])

settings_service = SettingsService()

@router.get("/")
async def get_user_settings() -> UserSettings:
    """
    获取当前用户的设置信息
    """
    logger.info("Retrieving current user settings")
    
    settings = settings_service.get_current_settings()
    logger.info(f"Retrieved user settings: theme={settings.theme}, language={settings.language}, notifications={settings.notifications}")
    
    return settings

@router.put("/")
async def update_user_settings(settings: UserSettings) -> Dict[str, str]:
    """
    更新当前用户的设置信息
    
    Args:
        settings: 用户设置对象，包含 theme、language、notifications 等字段
    """
    logger.info(f"Updating user settings: theme={settings.theme}, language={settings.language}, notifications={settings.notifications}")
    
    success = settings_service.update_settings(settings)
    if not success:
        error_msg = "Failed to update settings"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    logger.info("User settings updated successfully")
    return {"message": "Settings updated successfully"}

@router.get("/theme")
async def get_theme() -> Dict[str, str]:
    """
    获取当前主题设置
    """
    logger.info("Retrieving current theme setting")
    
    theme = settings_service.get_theme()
    logger.info(f"Current theme: {theme}")
    
    return {"theme": theme}

@router.put("/theme")
async def update_theme(theme: str) -> Dict[str, str]:
    """
    更新主题设置
    
    Args:
        theme: 主题名称，如 "light"、"dark"、"auto"
    """
    logger.info(f"Attempting to update theme to: {theme}")
    
    if theme not in ["light", "dark", "auto"]:
        error_msg = "Invalid theme value. Use 'light', 'dark', or 'auto'"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    success = settings_service.set_theme(theme)
    if not success:
        error_msg = "Failed to update theme"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    logger.info(f"Theme updated successfully to: {theme}")
    return {"message": f"Theme updated to {theme}"}

@router.get("/language")
async def get_language() -> Dict[str, str]:
    """
    获取当前语言设置
    """
    logger.info("Retrieving current language setting")
    
    language = settings_service.get_language()
    logger.info(f"Current language: {language}")
    
    return {"language": language}

@router.put("/language")
async def update_language(language: str) -> Dict[str, str]:
    """
    更新语言设置
    
    Args:
        language: 语言代码，如 "zh-CN"、"en-US"
    """
    logger.info(f"Attempting to update language to: {language}")
    
    if language not in ["zh-CN", "en-US"]:
        error_msg = "Invalid language value. Use 'zh-CN' or 'en-US'"
        logger.warning(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    success = settings_service.set_language(language)
    if not success:
        error_msg = "Failed to update language"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    logger.info(f"Language updated successfully to: {language}")
    return {"message": f"Language updated to {language}"}

@router.get("/notifications")
async def get_notifications() -> Dict[str, bool]:
    """
    获取通知设置
    """
    logger.info("Retrieving notification settings")
    
    notifications = settings_service.get_notifications()
    logger.info(f"Current notification settings: {notifications}")
    
    return notifications

@router.put("/notifications")
async def update_notifications(notifications: Dict[str, bool]) -> Dict[str, str]:
    """
    更新通知设置
    
    Args:
        notifications: 通知开关对象，如 {"email": true, "push": false}
    """
    logger.info(f"Updating notification settings: {notifications}")
    
    success = settings_service.set_notifications(notifications)
    if not success:
        error_msg = "Failed to update notifications"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    
    logger.info(f"Notification settings updated successfully: {notifications}")
    return {"message": "Notifications updated successfully"}