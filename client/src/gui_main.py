#!/usr/bin/env python3
"""
GUI客户端入口文件
"""

import sys
import os

# 正确设置项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# 添加项目根目录和client目录到sys.path
paths_to_add = [
    project_root,  # 项目根目录
    os.path.join(project_root, 'client'),  # client目录
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"🔧 添加的路径: {paths_to_add}")
print(f"📁 当前工作目录: {os.getcwd()}")

try:
    from client.gui.main_window import ModernChatGUI
    print("✅ 导入成功!")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print(f"📁 sys.path: {sys.path}")
    # 列出目录内容来调试
    print("📁 项目目录内容:")
    for item in os.listdir(project_root):
        print(f"  - {item}")
    raise

def main():
    """主函数"""
    print("🚀 启动多用户即时消息系统GUI客户端...")
    app = ModernChatGUI()
    app.run()

if __name__ == "__main__":
    main()