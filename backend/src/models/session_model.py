from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class SessionConversationItem(BaseModel):
    role: str  # "user" or "ai"
    content: str
    timestamp: datetime

class SessionModel(BaseModel):
    id: Optional[int] = None
    user_id: int
    session_id: str
    conversation: List[Dict[str, Any]] = []
    last_active: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
class SessionCreate(BaseModel):
    user_id: int
    session_id: Optional[str] = None
    conversation: List[SessionConversationItem] = []
    
class SessionUpdate(BaseModel):
    name: Optional[str] = None
    user_id: Optional[int] = None
    
class SessionSummary(BaseModel):
    session_id: str
    last_active: datetime
    conversation_length: int
    created_at: datetime