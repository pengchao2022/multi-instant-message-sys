import json
import asyncio
import websockets
import requests
import threading
import logging
import base64
import os
import mimetypes
from datetime import datetime

# 设置websockets日志级别
logging.getLogger('websockets').setLevel(logging.ERROR)

class SimpleChatClient:
    """简化的聊天客户端 - 使用HTTP API发送消息"""
    
    def __init__(self, gui_app):
        self.gui_app = gui_app
        self.websocket = None
        self.is_connected = False
        self.user_id = None
        self.username = None
        self.stop_listening = False
        self.server_url = None
        self.websocket_thread = None
        
        # 存储待发送的文件
        self.pending_files = []
        
    def set_server_info(self, server_url, user_id, username):
        """设置服务器信息"""
        self.server_url = server_url
        self.user_id = user_id
        self.username = username
        
    def add_pending_file(self, file_path):
        """添加待发送文件"""
        try:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # 读取文件数据
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            # 编码为base64
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # 获取MIME类型
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = "application/octet-stream"
            
            file_info = {
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "file_data": file_data_base64,
                "mime_type": mime_type,
                "is_image": mime_type.startswith('image/')
            }
            
            self.pending_files.append(file_info)
            print(f"📎 添加待发送文件: {file_name} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            print(f"❌ 添加文件失败: {str(e)}")
            return False
    
    def remove_pending_file(self, file_name):
        """移除待发送文件"""
        self.pending_files = [f for f in self.pending_files if f["file_name"] != file_name]
        print(f"🗑️ 移除待发送文件: {file_name}")
    
    def clear_pending_files(self):
        """清空待发送文件"""
        self.pending_files.clear()
        print("🧹 清空所有待发送文件")
    
    def get_pending_files_count(self):
        """获取待发送文件数量"""
        return len(self.pending_files)
    
    def send_message_with_files(self, text_content, receiver_id=None):
        """发送包含文本和文件的消息"""
        try:
            if not self.server_url:
                raise Exception("服务器地址未设置")
            
            # 构建消息数据
            message_data = {
                "sender_id": self.user_id,
                "sender_username": self.username,
                "text_content": text_content,
                "receiver_id": receiver_id,
                "message_type": "private" if receiver_id else "public",
                "timestamp": datetime.now().isoformat(),
                "files": self.pending_files.copy()  # 复制文件列表
            }
            
            print(f"📤 发送组合消息: 文本='{text_content}', 文件数量={len(self.pending_files)}")
            
            # 发送到服务器
            response = requests.post(
                f"{self.server_url}/send-message-with-files",
                json=message_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 组合消息发送成功")
                
                # 清空待发送文件
                self.clear_pending_files()
                
                return True
            else:
                error_msg = response.json().get('detail', '发送失败')
                print(f"❌ 组合消息发送失败: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ 发送组合消息错误: {str(e)}")
            return False

    # 原有的其他方法保持不变...
    def start_websocket_connection(self):
        """启动WebSocket连接"""
        try:
            print(f"🔗 启动WebSocket连接，用户ID: {self.user_id}")
            
            # 在新的线程中运行WebSocket连接
            self.websocket_thread = threading.Thread(
                target=self._run_websocket_loop,
                daemon=True
            )
            self.websocket_thread.start()
            
            print("✅ WebSocket连接线程已启动")
            return True
            
        except Exception as e:
            print(f"❌ 启动WebSocket连接失败: {str(e)}")
            return False
    
    def _run_websocket_loop(self):
        """在新的线程中运行WebSocket事件循环"""
        try:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行连接和监听
            loop.run_until_complete(self._websocket_main())
            
        except Exception as e:
            print(f"❌ WebSocket循环错误: {str(e)}")
    
    async def _websocket_main(self):
        """WebSocket主循环"""
        try:
            # 构建WebSocket URL
            ws_url = self.server_url.replace('http', 'ws') + f"/ws/{self.user_id}"
            print(f"🔗 连接WebSocket: {ws_url}")
            
            # 连接WebSocket
            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=10) as websocket:
                self.websocket = websocket
                self.is_connected = True
                
                print(f"✅ WebSocket连接成功! 用户: {self.username} (ID: {self.user_id})")
                
                # 通知GUI连接成功
                self.gui_app.root.after(0, self.gui_app.on_websocket_connected)
                
                # 监听消息
                await self._listen_for_messages()
                
        except Exception as e:
            print(f"❌ WebSocket连接错误: {str(e)}")
            self.is_connected = False
            self.gui_app.root.after(0, self.gui_app.on_websocket_disconnected, str(e))
    
    async def _listen_for_messages(self):
        """监听WebSocket消息"""
        try:
            while self.is_connected and not self.stop_listening:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    await self._handle_websocket_message(message)
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket连接已关闭")
                    break
                except Exception as e:
                    print(f"❌ 接收消息错误: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"❌ 监听循环错误: {str(e)}")
        finally:
            self.is_connected = False
            self.gui_app.root.after(0, self.gui_app.on_websocket_disconnected, "连接断开")
    
    async def _handle_websocket_message(self, message):
        """处理WebSocket消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            print(f"📨 收到WebSocket消息类型: {message_type}, 数据: {data}")
            
            # 处理不同类型的消息
            if message_type == "private_message":
                await self._handle_private_message(data)
            elif message_type == "group_message":
                await self._handle_group_message(data)
            elif message_type == "message_sent":
                await self._handle_message_sent(data)
            elif message_type == "user_status_update":
                await self._handle_user_status_update(data)
            elif message_type == "error":
                await self._handle_error_message(data)
            elif message_type == "file_message":
                await self._handle_file_message(data)
            elif message_type == "combined_message":
                await self._handle_combined_message(data)
            elif message_type == "pong":
                print("💓 收到心跳响应")
            else:
                print(f"⚠️ 未知消息类型: {message_type}")
                
        except Exception as e:
            print(f"❌ 处理WebSocket消息错误: {str(e)}")
    
    async def _handle_private_message(self, data):
        """处理私聊消息"""
        try:
            message_data = data.get('data', {})
            sender_id = message_data.get('sender_id')
            sender_username = message_data.get('sender_username', 'Unknown')
            content = message_data.get('content', '')
            timestamp = message_data.get('timestamp', '')
            
            print(f"📨 收到私聊消息: {sender_username} -> {content}")
            
            # 通知GUI处理私聊消息
            self.gui_app.root.after(0, self.gui_app.handle_private_message, 
                                  sender_id, sender_username, content, timestamp)
            
        except Exception as e:
            print(f"❌ 处理私聊消息错误: {str(e)}")
    
    async def _handle_group_message(self, data):
        """处理群聊消息"""
        try:
            message_data = data.get('data', {})
            sender_id = message_data.get('sender_id')
            sender_username = message_data.get('sender_username', 'Unknown')
            content = message_data.get('content', '')
            timestamp = message_data.get('timestamp', '')
            
            print(f"📢 收到群聊消息: {sender_username} -> {content}")
            
            # 通知GUI显示群聊消息（排除自己发送的消息）
            if sender_id != self.user_id:
                self.gui_app.root.after(0, lambda: self.gui_app.add_message_to_chat(
                    sender_username, content, "normal", timestamp
                ))
            
        except Exception as e:
            print(f"❌ 处理群聊消息错误: {str(e)}")
    
    async def _handle_combined_message(self, data):
        """处理组合消息（文本+文件）"""
        try:
            message_data = data.get('data', {})
            sender_id = message_data.get('sender_id')
            sender_username = message_data.get('sender_username', 'Unknown')
            text_content = message_data.get('text_content', '')
            files = message_data.get('files', [])
            timestamp = message_data.get('timestamp', '')
            
            print(f"📦 收到组合消息: {sender_username} -> 文本:'{text_content}', 文件:{len(files)}个")
            
            # 通知GUI处理组合消息
            self.gui_app.root.after(0, self.gui_app.handle_combined_message,
                                  sender_id, sender_username, text_content, files, timestamp)
            
        except Exception as e:
            print(f"❌ 处理组合消息错误: {str(e)}")
    
    async def _handle_file_message(self, data):
        """处理文件消息"""
        try:
            message_data = data.get('data', {})
            sender_id = message_data.get('sender_id')
            sender_username = message_data.get('sender_username', 'Unknown')
            file_name = message_data.get('file_name', '')
            file_data_base64 = message_data.get('file_data', '')
            file_size = message_data.get('file_size', 0)
            timestamp = message_data.get('timestamp', '')
            receiver_id = message_data.get('receiver_id')
            is_group_message = message_data.get('is_group_message', False)
            
            print(f"📎 收到文件消息: {sender_username} -> {file_name} ({file_size} bytes)")
            
            # 解码文件数据
            file_data = base64.b64decode(file_data_base64)
            
            # 通知GUI处理文件消息
            self.gui_app.root.after(0, self.gui_app.handle_file_message,
                                  sender_id, sender_username, file_name, file_data, 
                                  file_size, timestamp, receiver_id, is_group_message)
            
        except Exception as e:
            print(f"❌ 处理文件消息错误: {str(e)}")
            # 通知GUI显示错误
            self.gui_app.root.after(0, lambda: self.gui_app.add_message_to_chat(
                "系统", f"接收文件失败: {str(e)}", "system"
            ))
    
    async def _handle_message_sent(self, data):
        """处理消息发送确认"""
        try:
            message_data = data.get('data', {})
            delivered = message_data.get('delivered', False)
            receiver_id = message_data.get('receiver_id')
            content = message_data.get('content', '')
            message_type = message_data.get('message_type', 'text')
            
            if receiver_id:
                # 私聊消息确认
                if delivered:
                    if message_type == 'file':
                        print(f"✅ 文件消息已送达接收者 {receiver_id}")
                    else:
                        print(f"✅ 私聊消息已送达接收者 {receiver_id}")
                else:
                    if message_type == 'file':
                        print(f"⚠️ 文件消息未送达接收者 {receiver_id} (用户离线)")
                        self.gui_app.root.after(0, lambda: self.gui_app.add_message_to_chat(
                            "系统", f"用户离线，文件未送达", "system"
                        ))
                    else:
                        print(f"⚠️ 私聊消息未送达接收者 {receiver_id} (用户离线)")
                        self.gui_app.root.after(0, lambda: self.gui_app.add_message_to_chat(
                            "系统", f"用户离线，消息未送达", "system"
                        ))
            else:
                if message_type == 'file':
                    print(f"✅ 群聊文件消息发送成功")
                else:
                    print(f"✅ 群聊消息发送成功")
                
        except Exception as e:
            print(f"❌ 处理消息发送确认错误: {str(e)}")
    
    async def _handle_user_status_update(self, data):
        """处理用户状态更新"""
        try:
            user_data = data.get('data', {})
            user_id = user_data.get('user_id')
            username = user_data.get('username')
            status = user_data.get('status')
            
            print(f"🔄 用户状态更新: {username} -> {status}")
            
            # 刷新用户列表
            self.gui_app.root.after(0, self.gui_app.refresh_users)
            
        except Exception as e:
            print(f"❌ 处理用户状态更新错误: {str(e)}")
    
    async def _handle_error_message(self, data):
        """处理错误消息"""
        try:
            error_data = data.get('data', {})
            error_msg = error_data.get('message', '未知错误')
            
            print(f"❌ 收到错误消息: {error_msg}")
            
            self.gui_app.root.after(0, lambda: self.gui_app.add_message_to_chat(
                "系统", f"错误: {error_msg}", "system"
            ))
            
        except Exception as e:
            print(f"❌ 处理错误消息错误: {str(e)}")
    
    def send_message_via_http(self, content, receiver_id=None):
        """通过HTTP API发送消息"""
        try:
            if not self.server_url:
                raise Exception("服务器地址未设置")
                
            message_data = {
                "sender_id": self.user_id,
                "sender_username": self.username,
                "content": content,
                "receiver_id": receiver_id,
                "message_type": "private" if receiver_id else "public",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 通过HTTP发送消息: {message_data}")
            
            response = requests.post(
                f"{self.server_url}/send-message",
                json=message_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ HTTP消息发送成功: {result}")
                return True
            else:
                error_msg = response.json().get('detail', '发送失败')
                print(f"❌ HTTP消息发送失败: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ HTTP发送消息错误: {str(e)}")
            return False

    def send_file_via_http(self, file_path, receiver_id=None, is_group_message=False):
        """通过HTTP API发送文件"""
        try:
            if not self.server_url:
                raise Exception("服务器地址未设置")
            
            # 读取文件
            with open(file_path, 'rb') as file:
                file_data = file.read()
            
            # 编码为base64
            file_data_base64 = base64.b64encode(file_data).decode('utf-8')
            file_name = os.path.basename(file_path)
            file_size = len(file_data)
            
            file_message_data = {
                "sender_id": self.user_id,
                "sender_username": self.username,
                "file_name": file_name,
                "file_data": file_data_base64,
                "file_size": file_size,
                "receiver_id": receiver_id,
                "is_group_message": is_group_message,
                "message_type": "file",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📤 通过HTTP发送文件: {file_name} ({file_size} bytes)")
            
            response = requests.post(
                f"{self.server_url}/send-file",
                json=file_message_data,
                timeout=30  # 文件传输需要更长的超时时间
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ HTTP文件发送成功: {result}")
                return True
            else:
                error_msg = response.json().get('detail', '发送失败')
                print(f"❌ HTTP文件发送失败: {error_msg}")
                return False
                
        except Exception as e:
            print(f"❌ HTTP发送文件错误: {str(e)}")
            return False
    
    def stop_websocket(self):
        """停止WebSocket连接"""
        self.stop_listening = True
        self.is_connected = False
        
        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join(timeout=2.0)
        
        print("✅ WebSocket连接已停止")