import tkinter as tk
from tkinter import messagebox
import threading
import requests

class RegisterWindow:
    def __init__(self, parent, server_url):
        self.parent = parent
        self.server_url = server_url
        self.window = tk.Toplevel(parent)
        self.window.title("用户注册")
        self.window.geometry("600x600")
        self.window.configure(bg='#1E1E1E')
        self.window.resizable(False, False)
        
        self.title_font = ('Microsoft YaHei', 18, 'bold')
        self.normal_font = ('Microsoft YaHei', 12)
        self.small_font = ('Microsoft YaHei', 10)
        
        self.colors = {
            'background': '#1E1E1E',
            'surface': '#2D2D30',
            'primary': '#007ACC',
            'primary_hover': '#005A9E',
            'success': '#00FF00',
            'danger': '#D13438',
            'text_primary': '#00FF00',
            'text_secondary': '#00CC00',
            'border': '#3E3E42',
        }
        
        self.create_widgets()
        
    def create_widgets(self):
        main_container = tk.Frame(self.window, bg=self.colors['background'], padx=40, pady=40)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(
            main_container,
            text="用户注册",
            font=self.title_font,
            fg=self.colors['text_primary'],
            bg=self.colors['background'],
            pady=20
        )
        title_label.pack()
        
        # 注册卡片
        form_card = tk.Frame(main_container, bg=self.colors['surface'], padx=30, pady=30, relief='flat', bd=1)
        form_card.pack(fill='x', pady=20)
        
        # 用户名
        username_frame = tk.Frame(form_card, bg=self.colors['surface'])
        username_frame.pack(fill='x', pady=12)
        
        tk.Label(
            username_frame,
            text="用户名:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=10
        ).pack(side=tk.LEFT)
        
        self.username_entry = tk.Entry(
            username_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            width=25
        )
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 邮箱
        email_frame = tk.Frame(form_card, bg=self.colors['surface'])
        email_frame.pack(fill='x', pady=12)
        
        tk.Label(
            email_frame,
            text="邮箱:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=10
        ).pack(side=tk.LEFT)
        
        self.email_entry = tk.Entry(
            email_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            width=25
        )
        self.email_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 密码
        password_frame = tk.Frame(form_card, bg=self.colors['surface'])
        password_frame.pack(fill='x', pady=12)
        
        tk.Label(
            password_frame,
            text="密码:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=10
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
            width=25
        )
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 确认密码
        confirm_frame = tk.Frame(form_card, bg=self.colors['surface'])
        confirm_frame.pack(fill='x', pady=12)
        
        tk.Label(
            confirm_frame,
            text="确认密码:",
            font=self.normal_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            width=10
        ).pack(side=tk.LEFT)
        
        self.confirm_password_entry = tk.Entry(
            confirm_frame,
            font=self.normal_font,
            bg=self.colors['background'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='solid',
            bd=1,
            show="*",
            width=25
        )
        self.confirm_password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 按钮框架
        button_frame = tk.Frame(form_card, bg=self.colors['surface'], pady=5)
        button_frame.pack()
        
        self.register_button = tk.Button(
            button_frame,
            text="注册账号",
            font=self.normal_font,
            bg='#007ACC',
            fg='#00FF00',
            width=8,
            relief='flat',
            bd=0,
            cursor='hand2',
            command=self.register_user
        )
        self.register_button.pack(pady=5)
        
        self.cancel_button = tk.Button(
            button_frame,
            text="取消",
            font=self.normal_font,
            bg='#007ACC',
            fg='#00FF00',
            width=8,
            relief='flat',
            bd=0,
            cursor='hand2',
            command=self.window.destroy
        )
        self.cancel_button.pack(pady=5)
        
        # 状态标签
        self.status_label = tk.Label(
            form_card,
            text="请填写注册信息",
            font=self.small_font,
            fg=self.colors['text_primary'],
            bg=self.colors['surface'],
            pady=10
        )
        self.status_label.pack()
    
    def register_user(self):
        username = self.username_entry.get().strip()
        email = self.email_entry.get().strip()
        password = self.password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()
        
        if not username or not email or not password or not confirm_password:
            self.update_status("请填写所有字段", is_error=True)
            return
        
        if password != confirm_password:
            self.update_status("两次输入的密码不一致", is_error=True)
            return
        
        if len(password) < 6:
            self.update_status("密码长度至少6位", is_error=True)
            return
        
        self.update_status("正在注册...")
        self.register_button.config(state=tk.DISABLED)
        
        threading.Thread(
            target=self.async_register,
            args=(username, email, password),
            daemon=True
        ).start()
    
    def async_register(self, username, email, password):
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={
                    "username": username,
                    "email": email,
                    "password": password
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                self.window.after(0, self.on_register_success, username, result.get('user_id'))
            else:
                error_msg = response.json().get('detail', '注册失败')
                self.window.after(0, self.on_register_error, error_msg)
                
        except Exception as e:
            self.window.after(0, self.on_register_error, f"网络错误: {str(e)}")
    
    def on_register_success(self, username, user_id):
        self.update_status(f"注册成功！用户名: {username}", is_success=True)
        self.register_button.config(state=tk.NORMAL)
        
        if messagebox.askyesno("注册成功", f"用户 {username} 注册成功！\n是否自动填充登录信息？"):
            if hasattr(self.parent, 'fill_login_info'):
                self.parent.fill_login_info(username, "")
        
        self.window.after(3000, self.window.destroy)
    
    def on_register_error(self, error_message):
        self.update_status(f"注册失败: {error_message}", is_error=True)
        self.register_button.config(state=tk.NORMAL)
    
    def update_status(self, message, is_error=False, is_success=False):
        if is_error:
            color = self.colors['danger']
        elif is_success:
            color = self.colors['success']
        else:
            color = self.colors['text_primary']
        
        self.status_label.config(text=message, fg=color)