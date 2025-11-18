import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

import asyncio
import websockets
import json
from datetime import datetime
from typing import List, Callable, Any, Dict
from shared.protocols import *

class ChatClient:
    def __init__(self, server_url: str = "ws://localhost:8000"):
        self.server_url = server_url
        self.websocket = None
        self.user_id = None
        self.username = None
        self.is_connected = False
        self.message_handlers: List[Callable[[str, Dict[str, Any]], Any]] = []
        self.connection_handlers: List[Callable[[bool], Any]] = []
        self.user_status_handlers: List[Callable[[Dict[str, Any]], Any]] = []
    
    async def connect(self, user_id: int, username: str):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(f"{self.server_url}/ws/{user_id}")
            self.user_id = user_id
            self.username = username
            self.is_connected = True
            
            print(f"✅ 连接成功! 服务器: {self.server_url}")
            print(f"👤 用户: {username} (ID: {user_id})")
            
            # 通知连接处理器
            self._notify_connection_handlers(True)
            
            return True
            
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            self.is_connected = False
            self._notify_connection_handlers(False, str(e))
            raise
    
    async def receive_messages(self):
        """接收服务器消息"""
        try:
            async for message in self.websocket:
                await self.handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            print("❌ 连接已关闭")
            self.is_connected = False
            self._notify_connection_handlers(False, "连接已关闭")
        except Exception as e:
            print(f"❌ 接收消息错误: {e}")
            self.is_connected = False
            self._notify_connection_handlers(False, str(e))
    
    async def handle_message(self, message_data: str):
        """处理接收到的消息"""
        try:
            message = WSMessage.parse_raw(message_data)
            
            # 调用注册的消息处理器
            for handler in self.message_handlers:
                try:
                    await handler(message.type, message.data)
                except Exception as e:
                    print(f"消息处理器错误: {e}")
            
            # 特定消息类型的处理
            if message.type == WSMessageTypes.MESSAGE_RECEIVE:
                await self._handle_message_receive(message.data)
            elif message.type == WSMessageTypes.USER_STATUS_UPDATE:
                await self._handle_user_status_update(message.data)
            elif message.type == WSMessageTypes.TYPING_START:
                await self._handle_typing_start(message.data)
            elif message.type == WSMessageTypes.TYPING_STOP:
                await self._handle_typing_stop(message.data)
            elif message.type == "error":
                await self._handle_error_message(message.data)
            # 添加对 user_list 消息的处理
            elif message.type == "user_list":
                await self._handle_user_list(message.data)
                
        except Exception as e:
            print(f"❌ 处理消息错误: {e}")
    
    async def _handle_message_receive(self, data: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            msg_data = MessageResponse(**data)
            # 格式化消息显示
            timestamp = msg_data.timestamp.strftime('%H:%M:%S')
            if msg_data.receiver_id:
                # 私聊消息
                prefix = f"📨 [私聊]"
                message_type = "private"
            else:
                # 群聊消息
                prefix = f"💬"
                message_type = "group"
            
            formatted_message = f"{prefix} [{timestamp}] {msg_data.sender_username}: {msg_data.content}"
            print(f"\n{formatted_message}")
            
            # 通知GUI更新
            self._notify_message_handlers("message_received", {
                "sender": msg_data.sender_username,
                "content": msg_data.content,
                "timestamp": timestamp,
                "type": message_type,
                "receiver_id": msg_data.receiver_id,
                "is_own_message": msg_data.sender_id == self.user_id
            })
            
        except Exception as e:
            print(f"处理消息接收错误: {e}")
    
    async def _handle_user_status_update(self, data: Dict[str, Any]):
        """处理用户状态更新"""
        try:
            status_icons = {
                "online": "🟢",
                "offline": "⚫", 
                "away": "🟡"
            }
            icon = status_icons.get(data.get('status', ''), '⚫')
            status_message = f"{icon} [系统] 用户 {data.get('username', 'Unknown')} 状态变为 {data.get('status', 'unknown')}"
            print(f"\n{status_message}")
            
            # 通知GUI更新
            self._notify_user_status_handlers(data)
            self._notify_message_handlers("system_message", {
                "content": status_message,
                "type": "status_update"
            })
            
        except Exception as e:
            print(f"处理用户状态更新错误: {e}")
    
    async def _handle_typing_start(self, data: Dict[str, Any]):
        """处理开始输入指示"""
        try:
            typing_message = f"✍️  [系统] 用户 {data.get('user_id', 'Unknown')} 正在输入..."
            print(f"\n{typing_message}")
            
            self._notify_message_handlers("system_message", {
                "content": typing_message,
                "type": "typing_start"
            })
            
        except Exception as e:
            print(f"处理输入指示错误: {e}")
    
    async def _handle_typing_stop(self, data: Dict[str, Any]):
        """处理停止输入指示"""
        try:
            typing_message = f"✅ [系统] 用户 {data.get('user_id', 'Unknown')} 停止输入"
            print(f"\n{typing_message}")
            
            self._notify_message_handlers("system_message", {
                "content": typing_message,
                "type": "typing_stop"
            })
            
        except Exception as e:
            print(f"处理停止输入指示错误: {e}")
    
    async def _handle_error_message(self, data: Dict[str, Any]):
        """处理错误消息"""
        try:
            error_message = f"❌ [错误] {data.get('message', '未知错误')}"
            print(f"\n{error_message}")
            
            self._notify_message_handlers("system_message", {
                "content": error_message,
                "type": "error"
            })
            
        except Exception as e:
            print(f"处理错误消息错误: {e}")
    
    async def _handle_user_list(self, data: Dict[str, Any]):
        """处理用户列表"""
        try:
            users = data.get('users', [])
            # 通知GUI更新用户列表
            self._notify_message_handlers("user_list", {
                "users": users
            })
            
        except Exception as e:
            print(f"处理用户列表错误: {e}")
    
    def _notify_message_handlers(self, message_type: str, data: Dict[str, Any]):
        """通知消息处理器"""
        for handler in self.message_handlers:
            try:
                # 在适当的上下文中调用处理器
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(message_type, data))
                else:
                    handler(message_type, data)
            except Exception as e:
                print(f"通知消息处理器错误: {e}")
    
    def _notify_connection_handlers(self, connected: bool, error_message: str = None):
        """通知连接状态处理器"""
        for handler in self.connection_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(connected, error_message))
                else:
                    handler(connected, error_message)
            except Exception as e:
                print(f"通知连接处理器错误: {e}")
    
    def _notify_user_status_handlers(self, status_data: Dict[str, Any]):
        """通知用户状态处理器"""
        for handler in self.user_status_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(status_data))
                else:
                    handler(status_data)
            except Exception as e:
                print(f"通知用户状态处理器错误: {e}")
    
    def add_message_handler(self, handler: Callable[[str, Dict[str, Any]], Any]):
        """添加消息处理器"""
        self.message_handlers.append(handler)
    
    def add_connection_handler(self, handler: Callable[[bool, str], Any]):
        """添加连接状态处理器"""
        self.connection_handlers.append(handler)
    
    def add_user_status_handler(self, handler: Callable[[Dict[str, Any]], Any]):
        """添加用户状态处理器"""
        self.user_status_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable[[str, Dict[str, Any]], Any]):
        """移除消息处理器"""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    def remove_connection_handler(self, handler: Callable[[bool, str], Any]):
        """移除连接状态处理器"""
        if handler in self.connection_handlers:
            self.connection_handlers.remove(handler)
    
    def remove_user_status_handler(self, handler: Callable[[Dict[str, Any]], Any]):
        """移除用户状态处理器"""
        if handler in self.user_status_handlers:
            self.user_status_handlers.remove(handler)
    
    async def send_message(self, content: str, receiver_id: int = None, group_id: int = None):
        """发送消息"""
        if not self.is_connected:
            print("❌ 未连接到服务器")
            return False
        
        try:
            message = WSMessage(
                type=WSMessageTypes.MESSAGE_SEND,
                data={
                    "content": content,
                    "receiver_id": receiver_id,
                    "group_id": group_id
                }
            )
            
            await self.websocket.send(message.json())
            
            # 如果是私聊消息，在本地也显示
            if receiver_id:
                timestamp = datetime.now().strftime('%H:%M:%S')
                self._notify_message_handlers("message_sent", {
                    "sender": "你",
                    "content": content,
                    "timestamp": timestamp,
                    "type": "private",
                    "receiver_id": receiver_id,
                    "is_own_message": True
                })
            else:
                # 群聊消息在本地显示
                timestamp = datetime.now().strftime('%H:%M:%S')
                self._notify_message_handlers("message_sent", {
                    "sender": "你",
                    "content": content,
                    "timestamp": timestamp,
                    "type": "group",
                    "is_own_message": True
                })
            
            return True
        except Exception as e:
            print(f"❌ 发送消息失败: {e}")
            self._notify_message_handlers("system_message", {
                "content": f"发送消息失败: {e}",
                "type": "error"
            })
            return False
    
    async def start_typing(self):
        """开始输入指示"""
        if self.is_connected:
            try:
                message = WSMessage(type=WSMessageTypes.TYPING_START, data={})
                await self.websocket.send(message.json())
            except Exception as e:
                print(f"❌ 发送输入指示失败: {e}")
    
    async def stop_typing(self):
        """停止输入指示"""
        if self.is_connected:
            try:
                message = WSMessage(type=WSMessageTypes.TYPING_STOP, data={})
                await self.websocket.send(message.json())
            except Exception as e:
                print(f"❌ 停止输入指示失败: {e}")
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            self._notify_connection_handlers(False, "用户主动断开连接")
            print("✅ 已断开服务器连接")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "is_connected": self.is_connected,
            "server_url": self.server_url,
            "user_id": self.user_id,
            "username": self.username
        }

# 测试函数
async def test_connection():
    """测试连接"""
    client = ChatClient()
    try:
        await client.connect(1, "TestUser")
        print("连接测试成功!")
        
        # 添加测试消息处理器
        def test_handler(message_type: str, data: Dict[str, Any]):
            print(f"测试处理器 - 类型: {message_type}, 数据: {data}")
        
        client.add_message_handler(test_handler)
        
        # 测试发送消息
        await client.send_message("这是一条测试消息")
        await asyncio.sleep(2)
        
    except Exception as e:
        print(f"连接测试失败: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # 如果直接运行这个文件，启动测试
    asyncio.run(test_connection())