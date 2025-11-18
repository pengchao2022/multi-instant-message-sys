from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"

class UserStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"

# WebSocket消息协议
class WSMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = datetime.now()

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    status: UserStatus
    created_at: datetime

class MessageRequest(BaseModel):
    content: str
    message_type: MessageType = MessageType.TEXT
    receiver_id: Optional[int] = None  # 私聊
    group_id: Optional[int] = None     # 群聊

class MessageResponse(BaseModel):
    id: int
    content: str
    message_type: MessageType
    sender_id: int
    sender_username: str
    receiver_id: Optional[int]
    group_id: Optional[int]
    timestamp: datetime

class GroupCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_by: int
    created_at: datetime
    members: List[UserResponse] = []

# WebSocket特定消息类型
class WSMessageTypes:
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"
    MESSAGE_SEND = "message_send"
    MESSAGE_RECEIVE = "message_receive"
    USER_STATUS_UPDATE = "user_status_update"
    TYPING_START = "typing_start"
    TYPING_STOP = "typing_stop"