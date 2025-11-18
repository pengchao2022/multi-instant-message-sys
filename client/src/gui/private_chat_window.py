import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import threading

class PrivateChatWindow:
    """私聊窗口"""
    
    def __init__(self, parent, client, current_user, target_user):
        self.parent = parent
        self.client = client
        self.current_user = current_user
        self.target_user = target_user
        
        # 创建窗口
        self.window = tk.Toplevel(parent.root)
        self.window.title(f"私聊 - {target_user['username']} (ID: {target_user['id']})")
        self.window.geometry("700x800")
        self.window.configure(bg='#1E1E1E')
        self.window.minsize(400, 300)
        
        # 设置字体和颜色
        self.title_font = ('Microsoft YaHei', 14, 'bold')
        self.normal_font = ('Microsoft YaHei', 11)
        self.chat_font = ('Microsoft YaHei', 12)
        
        self.colors = {
            'background': '#1E1E1E',
            'surface': '#2D2D30',
            'primary': '#007ACC',
            'text_primary': '#00FF00',
            'text_secondary': '#00CC00',
            'private_message': '#B146C2',
            'danger': '#D13438',
            'warning': '#FFB900',
            'flash_color': '#FF6B6B'
        }
        
        self.create_widgets()
        self.setup_bindings()
        
        print(f"💬 打开与 {target_user['username']} 的私聊窗口")
    
    def create_widgets(self):
        """创建窗口部件"""
        # 主容器
        main_container = tk.Frame(self.window, bg=self.colors['background'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题栏
        title_frame = tk.Frame(main_container, bg=self.colors['surface'], height=60)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        title_frame.pack_propagate(False)
        
        title_container = tk.Frame(title_frame, bg=self.colors['surface'], padx=15, pady=10)
        title_container.pack(fill=tk.BOTH, expand=True)
        
        # 左侧标题信息
        title_info = tk.Frame(title_container, bg=self.colors['surface'])
        title_info.pack(side=tk.LEFT, fill=tk.Y)
        
        title_label = tk.Label(
            title_info,
            text=f"与 {self.target_user['username']} 私聊",
            font=self.title_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface']
        )
        title_label.pack(anchor='w')
        
        user_id_label = tk.Label(
            title_info,
            text=f"用户ID: {self.target_user['id']}",
            font=('Microsoft YaHei', 9),
            fg=self.colors['text_secondary'],
            bg=self.colors['surface']
        )
        user_id_label.pack(anchor='w')
        
        # 右侧关闭按钮
        close_button = tk.Button(
            title_container,
            text="关闭窗口",
            font=self.normal_font,
            bg=self.colors['danger'],
            fg='#00FF00',
            relief='flat',
            bd=0,
            command=self.on_close
        )
        close_button.pack(side=tk.RIGHT)
        
        # 聊天显示区域
        chat_display_frame = tk.Frame(main_container, bg=self.colors['background'])
        chat_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_display_frame,
            wrap=tk.WORD,
            font=self.chat_font,
            bg=self.colors['surface'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            state=tk.DISABLED,
            padx=15,
            pady=15,
            relief='solid',
            bd=1
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # 输入区域
        input_frame = tk.Frame(main_container, bg=self.colors['background'], height=70)
        input_frame.pack(fill=tk.X)
        input_frame.pack_propagate(False)
        
        input_container = tk.Frame(input_frame, bg=self.colors['surface'], padx=10, pady=10)
        input_container.pack(fill=tk.BOTH, expand=True)
        
        # 消息输入框
        self.message_entry = tk.Entry(
            input_container,
            font=self.chat_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 发送按钮
        self.send_button = tk.Button(
            input_container,
            text="发送",
            font=self.chat_font,
            bg=self.colors['primary'],
            fg='#00FF00',
            width=8,
            relief='flat',
            bd=0,
            command=self.send_private_message
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # 配置文本标签
        self.configure_tags()
        
        # 显示欢迎消息
        self.add_system_message(f"开始与 {self.target_user['username']} 私聊")
    
    def configure_tags(self):
        """配置文本标签样式"""
        self.chat_display.tag_config('system', foreground='#FF6B6B', font=('Microsoft YaHei', 10, 'italic'))
        self.chat_display.tag_config('private_self', foreground=self.colors['primary'], font=self.chat_font)
        self.chat_display.tag_config('private_other', foreground=self.colors['private_message'], font=self.chat_font)
        self.chat_display.tag_config('timestamp', foreground='#888888', font=('Microsoft YaHei', 9))
    
    def setup_bindings(self):
        """设置绑定"""
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.message_entry.bind('<Return>', self.send_private_message)
        self.message_entry.focus()
        
        # 设置窗口位置（稍微偏移避免完全重叠）
        self.window.geometry("+%d+%d" % (self.parent.root.winfo_x() + 50, self.parent.root.winfo_y() + 50))
    
    def add_system_message(self, message):
        """添加系统消息"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.chat_display.insert(tk.END, f"系统: {message}\n", 'system')
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def add_message_to_chat(self, sender, message, message_type="private_other", timestamp=None):
        """添加消息到私聊窗口"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%H:%M:%S')
        
        self.chat_display.config(state=tk.NORMAL)
        
        # 添加时间戳
        self.chat_display.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        
        if message_type == "private_self":
            self.chat_display.insert(tk.END, f"我: {message}\n", 'private_self')
        elif message_type == "private_other":
            self.chat_display.insert(tk.END, f"{sender}: {message}\n", 'private_other')
        else:
            self.chat_display.insert(tk.END, f"{sender}: {message}\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def send_private_message(self, event=None):
        """发送私聊消息"""
        if not hasattr(self.parent, 'is_connected') or not self.parent.is_connected:
            self.add_system_message("错误：未连接到服务器")
            return
        
        message = self.message_entry.get().strip()
        if not message:
            return
        
        # 在本地显示消息
        self.add_message_to_chat("我", message, "private_self")
        
        print(f"📤 发送私聊消息给 {self.target_user['username']} (ID: {self.target_user['id']}): {message}")
        
        # 通过HTTP发送私聊消息
        def send_message():
            try:
                # 使用正确的方法名 - 检查 chat_client.py 中的实际方法名
                if hasattr(self.client, 'send_private_message'):
                    success = self.client.send_private_message(self.target_user['id'], message)
                elif hasattr(self.client, 'send_message_via_http'):
                    # 如果只有通用的发送方法，添加私聊标识
                    success = self.client.send_message_via_http(message, self.target_user['id'])
                else:
                    print("❌ 没有找到可用的发送消息方法")
                    self.window.after(0, lambda: self.add_system_message("错误：客户端不支持发送消息"))
                    return
                
                if success:
                    print(f"✅ 私聊消息发送成功")
                    # 通知主窗口更新用户列表状态（标记有新消息）
                    if hasattr(self.parent, 'mark_user_has_new_message'):
                        self.parent.mark_user_has_new_message(self.target_user['id'])
                else:
                    print(f"❌ 私聊消息发送失败")
                    self.window.after(0, lambda: self.add_system_message("消息发送失败，请检查网络连接"))
            except Exception as error:
                print(f"❌ 私聊消息发送异常: {str(error)}")
                # 修复：在lambda中直接使用error变量
                error_msg = str(error)
                self.window.after(0, lambda msg=error_msg: self.add_system_message(f"发送错误: {msg}"))
        
        # 在新线程中发送消息
        threading.Thread(target=send_message, daemon=True).start()
        
        # 清空输入框
        self.message_entry.delete(0, tk.END)
    
    def receive_private_message(self, sender_username, content, timestamp=None):
        """接收私聊消息"""
        print(f"📨 在私聊窗口中收到来自 {sender_username} 的消息: {content}")
        self.add_message_to_chat(sender_username, content, "private_other", timestamp)
        
        # 如果窗口不在最前面，闪烁提醒
        if not self.is_window_focused():
            self.flash_window()
    
    def is_window_focused(self):
        """检查窗口是否获得焦点"""
        try:
            return self.window.focus_displayof() is not None
        except:
            return False
    
    def flash_window(self):
        """闪烁窗口标题提醒用户"""
        original_title = self.window.title()
        if not original_title.startswith("💬 "):
            self.window.title(f"💬 {original_title}")
            
            # 3秒后恢复原标题
            def restore_title():
                if self.window.winfo_exists():
                    self.window.title(original_title)
            
            self.window.after(3000, restore_title)
    
    def on_close(self):
        """关闭窗口"""
        print(f"💬 关闭与 {self.target_user['username']} 的私聊窗口")
        
        # 从父窗口的私聊窗口管理中移除
        if hasattr(self.parent, 'private_chat_windows'):
            if self.target_user['id'] in self.parent.private_chat_windows:
                del self.parent.private_chat_windows[self.target_user['id']]
                print(f"✅ 从私聊窗口管理中移除: {self.target_user['username']}")
        
        # 销毁窗口
        if self.window.winfo_exists():
            self.window.destroy()
    
    def focus_input(self):
        """聚焦到输入框"""
        if self.message_entry.winfo_exists():
            self.message_entry.focus()