from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class UserSettings(BaseModel):
    theme: str = "light"  # light, dark, auto
    language: str = "zh-CN"  # zh-CN, en-US
    notifications: Dict[str, bool] = {
        "email": True,
        "push": True,
        "weekly_summary": True
    }
    timezone: str = "Asia/Shanghai"
    default_chart_type: str = "bar"  # bar, line, pie, scatter
    
    class Config:
        from_attributes = True
        
class ThemeSettings(BaseModel):
    theme: str  # light, dark, auto
    
class LanguageSettings(BaseModel):
    language: str  # zh-CN, en-US
    
class NotificationSettings(BaseModel):
    email: bool = True
    push: bool = True
    weekly_summary: bool = True