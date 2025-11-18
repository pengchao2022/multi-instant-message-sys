import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import WebSocket
from sqlalchemy.orm import Session
from typing import Dict
import json

from src.shared.protocols import WSMessage, WSMessageTypes, MessageResponse
from server.models.user import Message

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_status: Dict[int, str] = {}
    
    async def connect(self, websocket: WebSocket, user):
        self.active_connections[user.id] = websocket
        self.user_status[user.id] = "online"
        
        # 广播用户上线状态
        await self.broadcast_user_status(user, "online")
        print(f"✅ User {user.username} (ID: {user.id}) connected. Total users: {len(self.active_connections)}")
        print(f"📊 Active connections: {list(self.active_connections.keys())}")
    
    def disconnect(self, user):
        if user.id in self.active_connections:
            del self.active_connections[user.id]
        if user.id in self.user_status:
            self.user_status[user.id] = "offline"
        print(f"🔌 User {user.username} (ID: {user.id}) disconnected. Total users: {len(self.active_connections)}")
        print(f"📊 Active connections: {list(self.active_connections.keys())}")
    
    async def send_personal_json(self, message: dict, user_id: int):
        """发送JSON消息给特定用户"""
        print(f"📤 Attempting to send message to user {user_id}")
        print(f"📤 Message type: {message.get('type')}")
        print(f"📤 Active connections: {list(self.active_connections.keys())}")
        
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                print(f"✅ Successfully sent message to user {user_id}")
                print(f"✅ Message content: {message.get('data', {}).get('content', 'No content')}")
                return True
            except Exception as e:
                print(f"❌ Error sending message to user {user_id}: {e}")
                # 清理失效的连接
                if user_id in self.active_connections:
                    del self.active_connections[user_id]
                return False
        else:
            print(f"⚠️ User {user_id} is not online, message not delivered")
            print(f"⚠️ Available users: {list(self.active_connections.keys())}")
            return False
    
    async def broadcast_json(self, message: dict, exclude_user_id: int = None):
        """广播JSON消息给所有用户"""
        disconnected = []
        print(f"📢 Broadcasting message to all users (excluding: {exclude_user_id})")
        
        for user_id, connection in self.active_connections.items():
            if user_id != exclude_user_id:
                try:
                    await connection.send_json(message)
                    print(f"✅ Broadcast to user {user_id}")
                except Exception as e:
                    print(f"❌ Error broadcasting to user {user_id}: {e}")
                    disconnected.append(user_id)
        
        # 清理断开的连接
        for user_id in disconnected:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
                print(f"🧹 Cleaned up disconnected user {user_id}")
    
    async def handle_message_send(self, message: WSMessage, sender, db: Session):
        try:
            print(f"🔄 [DEBUG] ====== 开始处理消息发送 ======")
            print(f"🔄 [DEBUG] 发送者: {sender.username} (ID: {sender.id})")
            print(f"🔄 [DEBUG] 消息类型: {message.type}")
            print(f"🔄 [DEBUG] 消息数据: {message.data}")
            print(f"🔄 [DEBUG] 当前活跃连接: {list(self.active_connections.keys())}")
            print(f"🔄 [DEBUG] 接收者ID: {message.data.get('receiver_id')}")
            
            # 检查消息数据
            if "content" not in message.data:
                error_msg = {
                    "type": "error",
                    "data": {"message": "消息内容不能为空"}
                }
                await self.send_personal_json(error_msg, sender.id)
                return
            
            # 保存消息到数据库
            db_message = Message(
                content=message.data["content"],
                message_type=message.data.get("message_type", "private"),
                sender_id=sender.id,
                receiver_id=message.data.get("receiver_id"),
                group_id=message.data.get("group_id"),
                timestamp=datetime.utcnow()
            )
            
            db.add(db_message)
            db.commit()
            db.refresh(db_message)
            
            print(f"💾 消息保存到数据库: ID {db_message.id}")
            
            # 构建响应消息
            response_data = {
                "id": db_message.id,
                "content": db_message.content,
                "message_type": db_message.message_type,
                "sender_id": sender.id,
                "sender_username": sender.username,
                "receiver_id": db_message.receiver_id,
                "group_id": db_message.group_id,
                "timestamp": db_message.timestamp.isoformat() if db_message.timestamp else None
            }
            
            # 发送消息给接收者或广播给所有用户
            if message.data.get("receiver_id"):
                # 私聊消息
                receiver_id = message.data["receiver_id"]
                print(f"📨 Private message from {sender.username} (ID: {sender.id}) to user ID: {receiver_id}")
                
                # 发送给接收者
                receiver_message = {
                    "type": "private_message",
                    "data": response_data
                }
                print(f"📨 Sending private message to receiver {receiver_id}")
                sent_to_receiver = await self.send_personal_json(receiver_message, receiver_id)
                
                # 发送确认消息给发送者
                sender_message = {
                    "type": "message_sent",
                    "data": {
                        **response_data,
                        "delivered": sent_to_receiver,
                        "receiver_online": sent_to_receiver
                    }
                }
                print(f"📨 Sending confirmation to sender {sender.id}")
                await self.send_personal_json(sender_message, sender.id)
                
                if sent_to_receiver:
                    print(f"✅ Private message delivered successfully to user {receiver_id}")
                else:
                    print(f"⚠️ Private message NOT delivered to user {receiver_id} (user offline)")
                
            else:
                # 群聊消息（广播给所有用户）
                broadcast_message = {
                    "type": "group_message", 
                    "data": response_data
                }
                print(f"📢 Broadcasting group message from {sender.username}")
                await self.broadcast_json(broadcast_message)
                
            print(f"✅ Message from {sender.username} processed successfully")
            print(f"🔄 [DEBUG] ====== 消息处理完成 ======")
            
        except Exception as e:
            print(f"❌ Error handling message: {e}")
            import traceback
            traceback.print_exc()
            
            # 发送错误消息给发送者
            error_msg = {
                "type": "error",
                "data": {"message": f"消息发送失败: {str(e)}"}
            }
            await self.send_personal_json(error_msg, sender.id)
            print(f"🔄 [DEBUG] ====== 消息处理失败 ======")
    
    async def broadcast_user_status(self, user, status: str):
        status_message = {
            "type": "user_status_update",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "status": status
            }
        }
        
        await self.broadcast_json(status_message)
        print(f"🔄 User {user.username} (ID: {user.id}) status updated to {status}")
    
    async def broadcast_typing(self, user_id: int, is_typing: bool):
        typing_message = {
            "type": "typing_start" if is_typing else "typing_stop",
            "data": {"user_id": user_id}
        }
        
        await self.broadcast_json(typing_message, exclude_user_id=user_id)
        print(f"⌨️ User {user_id} typing: {is_typing}")
    
    def disconnect_by_user_id(self, user_id: int):
        """通过用户ID断开连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_status:
            self.user_status[user_id] = "offline"
        print(f"🔌 User {user_id} disconnected by ID")
        print(f"📊 Active connections: {list(self.active_connections.keys())}")
    
    def get_online_users(self):
        """获取在线用户列表"""
        return list(self.active_connections.keys())