# Vercel Python Runtime 入口：把项目根目录加入模块搜索路径，暴露 ASGI 应用
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402
