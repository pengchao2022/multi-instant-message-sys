import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import requests
from datetime import datetime
import sys
import os
import tempfile
from PIL import Image, ImageTk
import base64

# 设置路径
current_dir = os.path.dirname(os.path.abspath(__file__))
client_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(client_dir)

# 添加项目根目录到sys.path
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"🔧 项目根目录: {project_root}")

# 现在应该可以正常导入了
from client.core.chat_client import SimpleChatClient
from client.gui.private_chat_window import PrivateChatWindow
from client.gui.register_window import RegisterWindow

print("✅ 所有导入成功!")

class ModernChatGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("多用户即时消息系统")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1E1E1E')
        
        # 设置字体
        self.title_font = ('Microsoft YaHei', 20, 'bold')
        self.subtitle_font = ('Microsoft YaHei', 14, 'bold')
        self.normal_font = ('Microsoft YaHei', 12)
        self.small_font = ('Microsoft YaHei', 10)
        self.chat_font = ('Microsoft YaHei', 13)
        
        # 颜色方案 - 绿色主题
        self.colors = {
            'background': '#1E1E1E',
            'surface': '#2D2D30',
            'primary': '#007ACC',
            'primary_hover': '#005A9E',
            'success': "#F7F9F7",
            'danger': '#D13438',
            'warning': '#FFB900',
            'text_primary': '#00FF00',
            'text_secondary': '#00CC00',
            'text_muted': '#009900',
            'border': '#3E3E42',
            'user_online': '#00FF00',
            'user_offline': '#666666',
            'message_self': '#004578',
            'message_other': '#2D2D30',
            'system_message': '#D13438',
            'private_message': '#B146C2',
            'file_message': '#FFA500',
            'flash_color': '#FF6B6B',
            'flash_text': '#FFFFFF',
            'input_bg': '#1E1E1E',
            'input_fg': '#00FF00',
            'file_preview_bg': '#2D2D30'
        }
        
        # 闪烁状态管理
        self.flashing_users = {}
        self.user_labels = {}
        self.users_with_new_messages = set()
        
        # 存储收到的私聊消息
        self.private_messages = {}
        
        # 客户端实例
        self.client = SimpleChatClient(self)
        self.is_connected = False
        self.current_user = None
        self.server_url = "http://localhost:8000"
        self.user_id_map = {}
        
        # 私聊窗口管理
        self.private_chat_windows = {}
        
        # 待发送文件管理
        self.pending_files = []
        self.pending_images = {}
        
        # 创建界面
        self.create_login_frame()
        self.create_chat_frame()
        
        # 隐藏聊天界面，先显示登录界面
        self.hide_chat_interface()
        
        print("🚀 GUI客户端启动完成")

    def create_login_frame(self):
        """创建登录界面"""
        self.login_frame = tk.Frame(self.root, bg=self.colors['background'], padx=40, pady=40)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # 主容器
        main_container = tk.Frame(self.login_frame, bg=self.colors['background'])
        main_container.pack(expand=True)
        
        # 标题
        title_label = tk.Label(
            main_container,
            text="多用户即时消息系统",
            font=self.title_font,
            fg=self.colors['text_primary'],
            bg=self.colors['background'],
            pady=20
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            main_container,
            text="登录到聊天服务器，与朋友们实时交流",
            font=self.small_font,
            fg=self.colors['text_secondary'],
            bg=self.colors['background'],
            pady=10
        )
        subtitle_label.pack()
        
        # 登录卡片
        login_card = tk.Frame(main_container, bg=self.colors['surface'], padx=30, pady=30, relief='flat', bd=1)
        login_card.pack(pady=30, fill='x', padx=50)
        
        # 服务器设置
        server_section = tk.Frame(login_card, bg=self.colors['surface'])
        server_section.pack(fill='x', pady=15)
        
        tk.Label(
            server_section,
            text="服务器设置",
            font=self.subtitle_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface']
        ).pack(anchor='w', pady=(0, 10))
        
        # 服务器地址
        server_url_frame = tk.Frame(server_section, bg=self.colors['surface'])
        server_url_frame.pack(fill='x', pady=8)
        
        tk.Label(
            server_url_frame,
            text="服务器地址:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=12
        ).pack(side=tk.LEFT)
        
        self.server_url_entry = tk.Entry(
            server_url_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            width=35
        )
        self.server_url_entry.insert(0, self.server_url)
        self.server_url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 登录信息
        login_section = tk.Frame(login_card, bg=self.colors['surface'])
        login_section.pack(fill='x', pady=15)
        
        tk.Label(
            login_section,
            text="登录信息",
            font=self.subtitle_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface']
        ).pack(anchor='w', pady=(0, 10))
        
        # 用户名
        username_frame = tk.Frame(login_section, bg=self.colors['surface'])
        username_frame.pack(fill='x', pady=8)
        
        tk.Label(
            username_frame,
            text="用户名:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=12
        ).pack(side=tk.LEFT)
        
        self.username_entry = tk.Entry(
            username_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            width=35
        )
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 密码
        password_frame = tk.Frame(login_section, bg=self.colors['surface'])
        password_frame.pack(fill='x', pady=8)
        
        tk.Label(
            password_frame,
            text="密码:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=12
        ).pack(side=tk.LEFT)
        
        self.password_entry = tk.Entry(
            password_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            show="*",
            width=35
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 按钮框架
        button_frame = tk.Frame(login_card, bg=self.colors['surface'], pady=20)
        button_frame.pack()
        
        self.login_button = tk.Button(
            button_frame,
            text="登录",
            font=self.normal_font,
            bg=self.colors['primary'],
            fg="#FF00A2",
            width=15,
            relief='flat',
            bd=0,
            command=self.login_to_server
        )
        self.login_button.pack(pady=5)
        
        self.register_button = tk.Button(
            button_frame,
            text="注册账号",
            font=self.normal_font,
            bg=self.colors['success'],
            fg="#FF00A2",
            width=15,
            relief='flat',
            bd=0,
            command=self.open_register_window
        )
        self.register_button.pack(pady=5)
        
        # 状态标签
        self.status_label = tk.Label(
            login_card,
            text="准备登录...",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            pady=10
        )
        self.status_label.pack()

    def create_chat_frame(self):
        """创建聊天界面 - 优化布局"""
        self.chat_frame = tk.Frame(self.root, bg=self.colors['background'])
        
        # 顶部状态栏
        status_bar = tk.Frame(self.chat_frame, bg=self.colors['surface'], height=50)
        status_bar.pack(fill=tk.X, padx=10, pady=5)
        status_bar.pack_propagate(False)
        
        # 左侧状态信息
        left_info = tk.Frame(status_bar, bg=self.colors['surface'])
        left_info.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        self.connection_status = tk.Label(
            left_info,
            text="未连接",
            font=self.normal_font,
            fg=self.colors['danger'],
            bg=self.colors['surface']
        )
        self.connection_status.pack(anchor='w')
        
        self.user_info = tk.Label(
            left_info,
            text="用户: 未登录",
            font=self.small_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface']
        )
        self.user_info.pack(anchor='w')
        
        # WebSocket状态
        self.websocket_status = tk.Label(
            left_info,
            text="WebSocket: 未连接",
            font=self.small_font,
            fg=self.colors['danger'],
            bg=self.colors['surface']
        )
        self.websocket_status.pack(anchor='w')
        
        # 右侧按钮
        right_buttons = tk.Frame(status_bar, bg=self.colors['surface'])
        right_buttons.pack(side=tk.RIGHT, fill=tk.Y, padx=10)
        
        self.disconnect_button = tk.Button(
            right_buttons,
            text="退出登录",
            font=self.normal_font,
            bg=self.colors['danger'],
            fg='#00FF00',
            relief='flat',
            bd=0,
            command=self.logout_from_server
        )
        self.disconnect_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = tk.Button(
            right_buttons,
            text="清空聊天",
            font=self.normal_font,
            bg=self.colors['warning'],
            fg='#FF00A2',
            relief='flat',
            bd=0,
            command=self.clear_chat
        )
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # 主内容区域 - 使用PanedWindow调整比例
        main_paned = tk.PanedWindow(self.chat_frame, orient=tk.HORIZONTAL, bg=self.colors['background'], sashrelief='raised', sashwidth=4)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 左侧聊天区域
        chat_container = tk.Frame(main_paned, bg=self.colors['background'])
        main_paned.add(chat_container, stretch="always", minsize=400)
        
        # 消息显示区域
        chat_display_frame = tk.Frame(chat_container, bg=self.colors['background'])
        chat_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
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
        
        # 输入区域 - 增加高度以容纳更多内容
        input_frame = tk.Frame(chat_container, bg=self.colors['background'], height=150)
        input_frame.pack(fill=tk.X, pady=5)
        input_frame.pack_propagate(False)
        
        input_container = tk.Frame(input_frame, bg=self.colors['surface'], padx=10, pady=10)
        input_container.pack(fill=tk.BOTH, expand=True)
        
        # 按钮行 - 水平排列
        button_row = tk.Frame(input_container, bg=self.colors['surface'])
        button_row.pack(fill=tk.X, pady=(0, 8))
        
        self.file_button = tk.Button(
            button_row,
            text="📎 添加文件",
            font=self.chat_font,
            bg=self.colors['primary'],
            fg='#FF00A2',
            width=12,
            relief='flat',
            bd=0,
            command=self.add_file_to_input
        )
        self.file_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.image_button = tk.Button(
            button_row,
            text="🖼️ 添加图片",
            font=self.chat_font,
            bg=self.colors['primary'],
            fg='#FF00A2',
            width=12,
            relief='flat',
            bd=0,
            command=self.add_image_to_input
        )
        self.image_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 清空按钮
        self.clear_input_button = tk.Button(
            button_row,
            text="🗑️ 清空",
            font=self.chat_font,
            bg=self.colors['danger'],
            fg='#FF00A2',
            width=8,
            relief='flat',
            bd=0,
            command=self.clear_input_area
        )
        self.clear_input_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # 文本输入框和发送按钮容器
        input_send_container = tk.Frame(input_container, bg=self.colors['surface'])
        input_send_container.pack(fill=tk.BOTH, expand=True)
        
        # 文本输入框 - 使用 Text 控件支持多行和文件预览
        self.message_input = tk.Text(
            input_send_container,
            height=4,
            wrap=tk.WORD,
            font=self.chat_font,
            bg=self.colors['input_bg'],
            fg=self.colors['input_fg'],
            insertbackground=self.colors['input_fg'],
            relief='solid',
            bd=1,
            padx=8,
            pady=8
        )
        self.message_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # 发送按钮 - 垂直排列
        send_button_container = tk.Frame(input_send_container, bg=self.colors['surface'])
        send_button_container.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.send_button = tk.Button(
            send_button_container,
            text="发送\n消息",
            font=('Microsoft YaHei', 11, 'bold'),
            bg=self.colors['success'],
            fg='#FF00A2',
            width=8,
            height=3,
            relief='flat',
            bd=0,
            command=self.send_combined_message
        )
        self.send_button.pack(fill=tk.BOTH, expand=True)
        
        # 右侧用户列表区域
        self.create_users_frame(main_paned)

    def create_users_frame(self, parent_paned):
        """创建在线用户列表"""
        users_container = tk.Frame(parent_paned, bg=self.colors['surface'], width=250)
        parent_paned.add(users_container, stretch="never", minsize=250)
        
        # 用户列表标题
        self.users_title = tk.Label(
            users_container,
            text="在线用户 (0/0)",
            font=self.subtitle_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            pady=15
        )
        self.users_title.pack(fill=tk.X, padx=10)
        
        # 用户列表框架
        list_container = tk.Frame(users_container, bg=self.colors['surface'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 创建Canvas和Scrollbar
        self.users_canvas = tk.Canvas(
            list_container,
            bg=self.colors['background'],
            highlightthickness=0,
            relief='solid',
            bd=1
        )
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.users_canvas.yview)
        self.users_canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建内部Frame用于放置用户标签
        self.users_inner_frame = tk.Frame(self.users_canvas, bg=self.colors['background'])
        
        # 将内部Frame添加到Canvas
        self.users_canvas_window = self.users_canvas.create_window(
            (0, 0), window=self.users_inner_frame, anchor="nw"
        )
        
        # 绑定配置事件以调整内部Frame大小
        self.users_inner_frame.bind(
            "<Configure>",
            lambda e: self.users_canvas.configure(scrollregion=self.users_canvas.bbox("all"))
        )
        
        self.users_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            self.users_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.users_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # 初始显示提示信息
        initial_label = tk.Label(
            self.users_inner_frame,
            text="请先登录",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['background'],
            pady=10
        )
        initial_label.pack(fill=tk.X, padx=5, pady=2)
        
        # 刷新按钮
        refresh_frame = tk.Frame(users_container, bg=self.colors['surface'], pady=10)
        refresh_frame.pack(fill=tk.X, padx=10)
        
        self.refresh_button = tk.Button(
            refresh_frame,
            text="刷新列表",
            font=self.normal_font,
            bg=self.colors['primary'],
            fg='#FF00A2',
            relief='flat',
            bd=0,
            command=self.refresh_users
        )
        self.refresh_button.pack(fill=tk.X)

    def add_file_to_input(self):
        """添加文件到输入框"""
        if not self.is_connected:
            messagebox.showerror("错误", "未连接到服务器")
            return
        
        file_path = filedialog.askopenfilename(
            title="选择要发送的文件",
            filetypes=[("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # 读取文件数据
                with open(file_path, 'rb') as file:
                    file_data = file.read()
                
                # 编码为base64
                file_data_base64 = base64.b64encode(file_data).decode('utf-8')
                
                # 获取MIME类型
                import mimetypes
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
                
                # 添加到待发送文件列表
                self.pending_files.append(file_info)
                
                # 在输入框中显示文件预览
                self.message_input.insert(tk.END, f"📎 {file_name}\n")
                
                print(f"📎 添加待发送文件: {file_name} ({file_size} bytes)")
                
            except Exception as e:
                print(f"❌ 添加文件失败: {str(e)}")
                messagebox.showerror("错误", f"添加文件失败: {str(e)}")

    def add_image_to_input(self):
        """添加图片到输入框"""
        if not self.is_connected:
            messagebox.showerror("错误", "未连接到服务器")
            return
        
        file_path = filedialog.askopenfilename(
            title="选择要发送的图片",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # 读取文件数据
                with open(file_path, 'rb') as file:
                    file_data = file.read()
                
                # 编码为base64
                file_data_base64 = base64.b64encode(file_data).decode('utf-8')
                
                # 创建图片预览
                image = Image.open(file_path)
                # 调整图片大小以适应输入框
                max_size = (80, 80)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 保存预览图片到临时文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                image.save(temp_file.name, 'PNG')
                temp_file.close()
                
                # 加载预览图片到Tkinter
                preview_image = ImageTk.PhotoImage(image)
                
                file_info = {
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_data": file_data_base64,
                    "mime_type": "image/jpeg",
                    "is_image": True,
                    "preview_image": preview_image,
                    "temp_file": temp_file.name
                }
                
                # 添加到待发送文件列表
                self.pending_files.append(file_info)
                # 保存图片引用防止被垃圾回收
                self.pending_images[file_name] = preview_image
                
                # 在输入框中显示图片预览
                image_label = tk.Label(self.message_input, image=preview_image, bg=self.colors['file_preview_bg'])
                self.message_input.window_create(tk.END, window=image_label)
                self.message_input.insert(tk.END, f" {file_name}\n")
                
                print(f"🖼️ 添加待发送图片: {file_name} ({file_size} bytes)")
                
            except Exception as e:
                print(f"❌ 添加图片失败: {str(e)}")
                messagebox.showerror("错误", f"添加图片失败: {str(e)}")

    def clear_pending_files(self):
        """清空待发送文件"""
        # 清理临时文件
        for file_info in self.pending_files:
            if file_info.get('temp_file') and os.path.exists(file_info['temp_file']):
                try:
                    os.unlink(file_info['temp_file'])
                except:
                    pass
        
        self.pending_files.clear()
        self.pending_images.clear()
        print("🧹 清空所有待发送文件")

    def clear_input_area(self):
        """清空输入区域"""
        self.message_input.delete("1.0", tk.END)
        self.clear_pending_files()
        print("🧹 清空输入框")

    def send_combined_message(self, event=None):
        """发送组合消息（文本+文件）"""
        if not self.is_connected:
            messagebox.showerror("错误", "未连接到服务器")
            return
        
        # 获取文本内容
        text_content = self.message_input.get("1.0", tk.END).strip()
        
        # 如果没有文本也没有文件，不发送
        if not text_content and not self.pending_files:
            messagebox.showwarning("提示", "请输入消息或添加文件")
            return
        
        # 显示发送的消息预览
        if text_content:
            self.add_message_to_chat("我", text_content, "own")
        
        # 显示文件预览
        for file_info in self.pending_files:
            file_name = file_info["file_name"]
            if file_info["is_image"]:
                self.add_message_to_chat("我", f"发送了图片: {file_name}", "system")
            else:
                self.add_message_to_chat("我", f"发送了文件: {file_name}", "system")
        
        print(f"📤 发送组合消息: 文本='{text_content}', 文件数量={len(self.pending_files)}")
        
        # 通过客户端发送组合消息
        def send_combined_message_thread():
            success = self.client.send_message_with_files(text_content)
            if success:
                print(f"✅ 组合消息发送成功")
                # 清空输入框和待发送文件
                self.root.after(0, self.clear_input_area)
            else:
                print(f"❌ 组合消息发送失败")
                self.root.after(0, lambda: self.add_message_to_chat(
                    "系统", "消息发送失败，请检查网络连接", "system"
                ))
        
        threading.Thread(target=send_combined_message_thread, daemon=True).start()

    def handle_combined_message(self, sender_id, sender_username, text_content, files, timestamp):
        """处理收到的组合消息"""
        try:
            print(f"📦 收到组合消息: {sender_username} -> 文本:'{text_content}', 文件:{len(files)}个")
            
            # 显示文本消息
            if text_content:
                self.add_message_to_chat(sender_username, text_content, "normal", timestamp)
            
            # 显示文件消息
            for file_info in files:
                file_name = file_info.get('file_name', '')
                file_size = file_info.get('file_size', 0)
                is_image = file_info.get('is_image', False)
                
                if is_image:
                    display_text = f"📷 图片: {file_name} ({self.format_file_size(file_size)})"
                else:
                    display_text = f"📎 文件: {file_name} ({self.format_file_size(file_size)})"
                
                self.add_message_to_chat(sender_username, display_text, "normal", timestamp)
                
        except Exception as e:
            print(f"❌ 处理组合消息错误: {str(e)}")

    def handle_file_message(self, message_data):
        """处理收到的文件消息"""
        try:
            sender_username = message_data.get('sender_username', 'Unknown')
            file_name = message_data.get('file_name', '')
            file_size = message_data.get('file_size', 0)
            message_type = message_data.get('message_type', 'file')
            download_url = message_data.get('content', '')
            timestamp = message_data.get('timestamp', '')
            
            # 格式化文件大小
            size_str = self.format_file_size(file_size)
            
            if message_type == "image":
                display_text = f"📷 图片: {file_name} ({size_str})"
            else:
                display_text = f"📎 文件: {file_name} ({size_str})"
            
            # 创建可点击的文件链接
            self.add_file_message_to_chat(sender_username, display_text, download_url, file_name, timestamp)
            
        except Exception as e:
            print(f"❌ 处理文件消息错误: {str(e)}")

    def add_file_message_to_chat(self, sender, display_text, download_url, file_name, timestamp=None):
        """添加文件消息到聊天显示区域"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%H:%M:%S')
        
        self.chat_display.config(state=tk.NORMAL)
        
        # 插入消息
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {display_text}\n")
        
        # 使文件消息可点击
        start_index = self.chat_display.index("end-2l")
        self.chat_display.insert(tk.END, f"    📥 点击下载\n")
        end_index = self.chat_display.index("end-1l")
        
        # 添加点击事件
        def on_file_click(event):
            self.download_file(download_url, file_name)
        
        # 创建标签用于点击
        self.chat_display.tag_add("file_link", start_index, end_index)
        self.chat_display.tag_config("file_link", foreground=self.colors['file_message'], underline=True)
        self.chat_display.tag_bind("file_link", "<Button-1>", on_file_click)
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def download_file(self, download_url, file_name):
        """下载文件"""
        def download_thread():
            try:
                save_path = filedialog.asksaveasfilename(
                    title="保存文件",
                    initialfile=file_name
                )
                
                if save_path:
                    response = requests.get(f"{self.server_url}{download_url}", stream=True)
                    if response.status_code == 200:
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                        
                        print(f"✅ 文件下载成功: {file_name}")
                        self.add_message_to_chat("系统", f"文件已保存到: {os.path.basename(save_path)}", "system")
                    else:
                        print(f"❌ 文件下载失败: {response.status_code}")
                        self.add_message_to_chat("系统", f"文件下载失败: HTTP {response.status_code}", "system")
                    
            except Exception as e:
                print(f"❌ 文件下载错误: {str(e)}")
                self.add_message_to_chat("系统", f"文件下载错误: {str(e)}", "system")
        
        threading.Thread(target=download_thread, daemon=True).start()

    def format_file_size(self, size_bytes):
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names)-1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"

    def on_user_click(self, event, user_id):
        """用户标签点击事件"""
        if not self.is_connected:
            return
        
        if user_id != self.current_user['id']:
            # 停止闪烁（用户发现了消息）
            self.stop_user_flash(user_id)
            # 从有新消息的用户集合中移除
            if user_id in self.users_with_new_messages:
                self.users_with_new_messages.remove(user_id)
            # 打开私聊窗口
            if user_id in self.user_id_map:
                self.open_private_chat(user_id, self.user_id_map[user_id])

    def open_private_chat(self, target_user_id, target_user_info):
        """打开私聊窗口"""
        # 检查是否已经打开了该用户的私聊窗口
        if target_user_id in self.private_chat_windows:
            # 如果窗口已存在，将其提到前台
            window = self.private_chat_windows[target_user_id]
            window.window.lift()
            window.window.focus_force()
            
            # 如果窗口存在且有历史消息，确保显示所有消息
            if target_user_id in self.private_messages:
                for msg in self.private_messages[target_user_id]:
                    window.receive_private_message(
                        msg['sender'], 
                        msg['content'], 
                        msg['timestamp']
                    )
            return
        
        # 确保 target_user_info 包含 id
        if 'id' not in target_user_info:
            target_user_info['id'] = target_user_id
        
        print(f"💬 打开与 {target_user_info['username']} (ID: {target_user_info['id']}) 的私聊窗口")
        
        # 创建新的私聊窗口
        private_window = PrivateChatWindow(
            self, self.client, self.current_user, target_user_info
        )
        
        # 保存窗口引用
        self.private_chat_windows[target_user_id] = private_window
        
        # 如果有历史消息，显示所有消息
        if target_user_id in self.private_messages:
            for msg in self.private_messages[target_user_id]:
                private_window.receive_private_message(
                    msg['sender'], 
                    msg['content'], 
                    msg['timestamp']
                )

    def handle_private_message(self, sender_id, sender_username, content, timestamp):
        """处理收到的私聊消息"""
        print(f"📨 处理私聊消息: {sender_username} -> {content}")
        
        # 存储私聊消息
        if sender_id not in self.private_messages:
            self.private_messages[sender_id] = []
        
        self.private_messages[sender_id].append({
            'sender': sender_username,
            'content': content,
            'timestamp': timestamp
        })
        
        # 检查是否已经打开了该用户的私聊窗口
        if sender_id in self.private_chat_windows:
            # 如果窗口已存在，将消息添加到该窗口
            private_window = self.private_chat_windows[sender_id]
            private_window.receive_private_message(sender_username, content, timestamp)
        else:
            # 如果窗口不存在，在主聊天窗口显示提示
            self.add_message_to_chat(
                "系统", 
                f"收到来自 {sender_username} 的私聊消息: {content} (点击用户名打开私聊窗口)", 
                "system"
            )
            
            # 标记用户有新消息
            self.users_with_new_messages.add(sender_id)
            
            # 闪烁用户列表中的对应项
            self.flash_user_in_list(sender_id)
            
            # 闪烁窗口任务栏
            self.flash_window_taskbar()

    def mark_user_has_new_message(self, user_id):
        """标记用户有新消息（用于发送方）"""
        print(f"💫 标记用户 {user_id} 有新消息发送")

    def flash_user_in_list(self, user_id):
        """闪烁用户列表中的用户项"""
        if user_id not in self.user_id_map:
            return
        
        username = self.user_id_map[user_id]['username']
        print(f"💫 用户 {username} 有新消息，在列表中闪烁提醒")
        
        # 如果用户已经在闪烁，先停止之前的闪烁
        if user_id in self.flashing_users:
            self.stop_user_flash(user_id)
        
        # 开始持续闪烁动画
        self.start_continuous_flash_animation(user_id)

    def start_continuous_flash_animation(self, user_id):
        """开始持续闪烁动画（直到用户点击）"""
        if user_id not in self.user_labels:
            return
            
        label = self.user_labels[user_id]
        is_red = [False]
        current_timer = [None]
        
        def flash_step():
            # 如果用户不再需要闪烁（比如用户点击了），则停止
            if user_id not in self.users_with_new_messages:
                if user_id in self.flashing_users:
                    del self.flashing_users[user_id]
                return
                
            # 切换闪烁状态
            if is_red[0]:
                # 恢复正常状态
                self.update_user_label_appearance(user_id, is_flashing=False)
                is_red[0] = False
            else:
                # 闪烁状态：红色背景
                label.config(bg=self.colors['flash_color'], fg=self.colors['flash_text'])
                is_red[0] = True
            
            # 继续下一次闪烁
            current_timer[0] = self.root.after(600, flash_step)
            # 更新存储的定时器ID
            if user_id in self.flashing_users:
                self.flashing_users[user_id]['timer'] = current_timer[0]
        
        # 初始化闪烁状态
        self.flashing_users[user_id] = {
            'timer': None,
            'is_red': False
        }
        
        # 开始闪烁
        flash_step()

    def stop_user_flash(self, user_id):
        """停止用户闪烁"""
        if user_id in self.flashing_users:
            flash_data = self.flashing_users[user_id]
            if flash_data['timer']:
                try:
                    self.root.after_cancel(flash_data['timer'])
                except:
                    pass
            del self.flashing_users[user_id]
            
        # 恢复用户显示状态
        if user_id in self.user_labels:
            self.update_user_label_appearance(user_id, is_flashing=False)

    def update_user_label_appearance(self, user_id, is_flashing=False):
        """更新用户标签的外观"""
        if user_id not in self.user_labels or user_id not in self.user_id_map:
            return
            
        label = self.user_labels[user_id]
        user_info = self.user_id_map[user_id]
        username = user_info['username']
        status = user_info['status']
        
        if user_id == self.current_user['id']:
            display_text = f"{username} (我)"
        else:
            display_text = username
            
        if status == "online":
            display_text += " ● 在线"
        else:
            display_text += " ○ 离线"
            
        # 如果有新消息但不在闪烁状态，显示新消息标识但不闪烁
        if user_id in self.users_with_new_messages and not is_flashing:
            display_text += " 🔴 新消息"
            label.config(
                text=display_text,
                bg=self.colors['background'],
                fg=self.colors['text_primary']
            )
        elif is_flashing:
            # 闪烁状态
            label.config(
                text=display_text + " 🔴 新消息",
                bg=self.colors['flash_color'],
                fg=self.colors['flash_text']
            )
        else:
            # 正常状态
            label.config(
                text=display_text,
                bg=self.colors['background'],
                fg=self.colors['text_primary']
            )

    def flash_window_taskbar(self):
        """闪烁窗口任务栏图标（跨平台）"""
        # 保存原始标题
        original_title = self.root.title()
        
        # 添加闪烁标识
        if not original_title.startswith("💬 "):
            self.root.title(f"💬 {original_title}")
            
            # 3秒后恢复原标题
            self.root.after(3000, lambda: self.root.title(original_title))

    def hide_chat_interface(self):
        """隐藏聊天界面"""
        if hasattr(self, 'chat_frame') and self.chat_frame.winfo_ismapped():
            self.chat_frame.pack_forget()

    def show_chat_interface(self):
        """显示聊天界面"""
        self.login_frame.pack_forget()
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update()

    def show_login_interface(self):
        """显示登录界面"""
        self.hide_chat_interface()
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        self.root.update()

    def update_status(self, message, is_error=False, is_success=False):
        """更新状态信息"""
        if is_error:
            color = self.colors['danger']
        elif is_success:
            color = self.colors['success']
        else:
            color = self.colors['text_primary']
        
        self.status_label.config(text=message, fg=color)

    def add_message_to_chat(self, sender, message, message_type="normal", timestamp=None):
        """添加消息到聊天显示区域"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%H:%M:%S')
        
        self.chat_display.config(state=tk.NORMAL)
        
        if message_type == "system":
            self.chat_display.insert(tk.END, f"[{timestamp}] 系统: {message}\n", 'system')
        elif message_type == "private":
            self.chat_display.insert(tk.END, f"[{timestamp}] 私聊 {sender}: {message}\n", 'private')
        elif message_type == "own":
            self.chat_display.insert(tk.END, f"[{timestamp}] 我: {message}\n", 'own')
        else:
            self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def clear_chat(self):
        """清空聊天记录"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        self.add_message_to_chat("系统", "聊天记录已清空", "system")

    def open_register_window(self):
        """打开注册窗口"""
        server_url = self.server_url_entry.get().strip() or self.server_url
        RegisterWindow(self.root, server_url)

    def fill_login_info(self, username, password):
        """填充登录信息"""
        self.username_entry.delete(0, tk.END)
        self.username_entry.insert(0, username)
        self.password_entry.delete(0, tk.END)
        self.password_entry.insert(0, password)

    def login_to_server(self):
        """登录到服务器"""
        server_url = self.server_url_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not server_url or not username or not password:
            messagebox.showerror("错误", "请填写所有字段")
            return
        
        self.update_status("正在登录...")
        self.login_button.config(state=tk.DISABLED)
        self.register_button.config(state=tk.DISABLED)
        
        threading.Thread(
            target=self.async_login,
            args=(server_url, username, password),
            daemon=True
        ).start()

    def async_login(self, server_url, username, password):
        """异步登录服务器"""
        try:
            response = requests.post(
                f"{server_url}/login",
                json={
                    "username": username,
                    "password": password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                user_id = result.get('user_id')
                access_token = result.get('access_token')
                
                print(f"✅ 登录成功! 用户ID: {user_id}, 用户名: {username}")
                
                self.current_user = {
                    'id': user_id,
                    'username': username,
                    'token': access_token
                }
                
                self.server_url = server_url
                # 设置客户端服务器信息
                self.client.set_server_info(server_url, user_id, username)
                
                # 更新UI状态
                self.root.after(0, self.on_login_success, user_id, username)
                
            else:
                error_msg = response.json().get('detail', '登录失败')
                print(f"❌ 登录失败: {error_msg}")
                self.root.after(0, self.on_login_error, error_msg)
                
        except Exception as e:
            print(f"❌ 登录网络错误: {str(e)}")
            self.root.after(0, self.on_login_error, f"网络错误: {str(e)}")

    def on_login_success(self, user_id, username):
        """登录成功回调"""
        print(f"✅ 登录成功回调 - 用户: {username}, ID: {user_id}")
        self.is_connected = True
        self.show_chat_interface()
        self.user_info.config(text=f"用户: {username} (ID: {user_id})", fg=self.colors['text_primary'])
        self.connection_status.config(text="HTTP已连接", fg=self.colors['success'])
        self.websocket_status.config(text="WebSocket: 连接中...", fg=self.colors['warning'])
        self.add_message_to_chat("系统", f"欢迎 {username}！登录成功！", "system")
        self.update_status("登录成功", is_success=True)
        
        # 启动WebSocket连接
        print("🔗 启动WebSocket连接...")
        websocket_success = self.client.start_websocket_connection()
        if not websocket_success:
            self.websocket_status.config(text="WebSocket: 连接失败", fg=self.colors['danger'])
            self.add_message_to_chat("系统", "WebSocket连接失败，无法接收实时消息", "system")
        
        # 登录后立即请求用户列表
        print("🔄 登录成功后请求用户列表...")
        self.refresh_users()

    def on_websocket_connected(self):
        """WebSocket连接成功回调"""
        print("✅ WebSocket连接成功回调")
        self.websocket_status.config(text="WebSocket: 已连接", fg=self.colors['success'])
        self.add_message_to_chat("系统", "实时消息连接已建立", "system")

    def on_websocket_disconnected(self, reason=""):
        """WebSocket连接断开回调"""
        print(f"❌ WebSocket连接断开: {reason}")
        self.websocket_status.config(text="WebSocket: 未连接", fg=self.colors['danger'])
        if reason:
            self.add_message_to_chat("系统", f"实时消息连接断开: {reason}", "system")

    def on_login_error(self, error_message):
        """登录失败回调"""
        print(f"❌ 登录失败回调: {error_message}")
        self.login_button.config(state=tk.NORMAL)
        self.register_button.config(state=tk.NORMAL)
        self.update_status(f"登录失败: {error_message}", is_error=True)
        messagebox.showerror("登录错误", f"登录失败:\n{error_message}")

    def logout_from_server(self):
        """退出登录"""
        self.is_connected = False
        
        # 停止所有闪烁
        for user_id in list(self.flashing_users.keys()):
            self.stop_user_flash(user_id)
        
        # 清空有新消息的用户集合和私聊消息
        self.users_with_new_messages.clear()
        self.private_messages.clear()
        
        # 清空待发送文件
        self.clear_pending_files()
        
        # 停止WebSocket连接
        self.client.stop_websocket()
        
        # 关闭所有私聊窗口
        for window in list(self.private_chat_windows.values()):
            window.on_close()
        
        self.on_logout()

    def on_logout(self):
        """退出登录回调"""
        self.is_connected = False
        self.current_user = None
        self.show_login_interface()
        self.login_button.config(state=tk.NORMAL)
        self.register_button.config(state=tk.NORMAL)
        self.update_status("已退出登录")
        self.connection_status.config(text="未连接", fg=self.colors['danger'])
        self.websocket_status.config(text="WebSocket: 未连接", fg=self.colors['danger'])
        self.clear_chat()
        self.update_user_list([])

    def send_message(self, event=None):
        """发送消息（群聊）- 保留原有功能"""
        if not self.is_connected:
            messagebox.showerror("错误", "未连接到服务器")
            return
        
        message = self.message_input.get("1.0", tk.END).strip()
        if not message:
            return
        
        # 发送普通群聊消息
        self.add_message_to_chat("我", message, "own")
        print(f"📤 发送群聊消息: {message}")
        
        # 通过HTTP发送普通消息
        def send_normal_message():
            success = self.client.send_message_via_http(message)
            if success:
                print(f"✅ 群聊消息发送成功")
                self.root.after(0, self.clear_input_area)
            else:
                print(f"❌ 群聊消息发送失败")
                self.root.after(0, lambda: self.add_message_to_chat(
                    "系统", f"消息发送失败，请检查网络连接", "system"
                ))
        
        threading.Thread(target=send_normal_message, daemon=True).start()

    def refresh_users(self):
        """刷新用户列表"""
        if not self.is_connected:
            print("❌ 刷新用户列表失败: 未连接")
            return
        
        print("🔄 开始刷新用户列表...")
        
        def fetch_users():
            try:
                print(f"🌐 请求用户列表: {self.server_url}/users")
                response = requests.get(f"{self.server_url}/users", timeout=5)
                print(f"📊 用户列表响应状态: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📋 用户列表数据: {data}")
                    users = data.get('users', [])
                    print(f"👥 解析到 {len(users)} 个用户")
                    self.root.after(0, self.update_user_list, users)
                else:
                    print(f"❌ 获取用户列表失败: {response.status_code}")
                    self.root.after(0, lambda: self.add_message_to_chat(
                        "系统", "获取用户列表失败", "system"
                    ))
            except Exception as e:
                print(f"❌ 请求用户列表错误: {str(e)}")
                self.root.after(0, lambda: self.add_message_to_chat(
                    "系统", f"获取用户列表错误: {str(e)}", "system"
                ))
        
        threading.Thread(target=fetch_users, daemon=True).start()

    def update_user_list(self, users):
        """更新用户列表"""
        print(f"🔄 更新用户列表界面，收到 {len(users)} 个用户")
        
        # 清除现有用户标签
        for widget in self.users_inner_frame.winfo_children():
            widget.destroy()
        self.user_labels.clear()
        
        if not users:
            print("📝 没有用户数据，显示'暂无用户'")
            no_users_label = tk.Label(
                self.users_inner_frame,
                text="暂无用户",
                font=self.normal_font,
                fg=self.colors['text_primary'],
                bg=self.colors['background'],
                pady=10
            )
            no_users_label.pack(fill=tk.X, padx=5, pady=2)
            self.users_title.config(text="在线用户 (0/0)")
            return
        
        self.user_id_map = {}
        
        online_count = 0
        for user in users:
            user_id = user.get('id')
            username = user.get('username')
            status = user.get('status', 'offline')
            
            print(f"👤 处理用户: {username}, ID: {user_id}, 状态: {status}")
            
            # 确保 user_info 包含所有必要字段
            self.user_id_map[user_id] = {
                'id': user_id,
                'username': username,
                'status': status
            }
            
            # 创建用户标签
            if user_id == self.current_user['id']:
                display_text = f"{username} (我)"
            else:
                display_text = username
                
            if status == "online":
                online_count += 1
                display_text += " ● 在线"
            else:
                display_text += " ○ 离线"
            
            # 如果有新消息，添加新消息标识
            if user_id in self.users_with_new_messages:
                display_text += " 🔴 新消息"
            
            # 创建可点击的用户标签
            user_label = tk.Label(
                self.users_inner_frame,
                text=display_text,
                font=self.normal_font,
                fg=self.colors['text_primary'],
                bg=self.colors['background'],
                padx=10,
                pady=8,
                cursor="hand2",
                anchor='w'
            )
            
            # 绑定点击事件（除了当前用户）
            if user_id != self.current_user['id']:
                user_label.bind("<Button-1>", lambda e, uid=user_id: self.on_user_click(e, uid))
            
            user_label.pack(fill=tk.X, padx=5, pady=2)
            self.user_labels[user_id] = user_label
            
            print(f"✅ 添加用户到列表: {display_text}")
            
            # 如果用户有新消息，重新开始闪烁
            if user_id in self.users_with_new_messages and user_id not in self.flashing_users:
                self.flash_user_in_list(user_id)
        
        title_text = f"在线用户 ({online_count}/{len(users)})"
        print(f"📊 更新标题: {title_text}")
        self.users_title.config(text=title_text)
        
        print(f"✅ 用户列表更新完成，在线: {online_count}, 总计: {len(users)}")
        
        # 更新Canvas的滚动区域
        self.users_inner_frame.update_idletasks()
        self.users_canvas.configure(scrollregion=self.users_canvas.bbox("all"))

    def run(self):
        """运行GUI"""
        self.chat_display.tag_config('system', foreground=self.colors['system_message'])
        self.chat_display.tag_config('private', foreground=self.colors['private_message'])
        self.chat_display.tag_config('own', foreground=self.colors['primary'])
        self.chat_display.tag_config('file_link', foreground=self.colors['file_message'], underline=True)
        
        self.root.eval('tk::PlaceWindow . center')
        
        print("🎮 启动GUI主循环...")
        self.root.mainloop()

# 如果这是主文件，启动应用
if __name__ == "__main__":
    app = ModernChatGUI()
    app.run()