#!/usr/bin/env python3
"""
运行GUI客户端的脚本
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from client.gui_main import main

if __name__ == "__main__":
    main()