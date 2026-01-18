"""
API Package - 初始化
"""

# 修复导入路径问题
import sys
from pathlib import Path

# 确保可以正确导入logging_config
api_dir = Path(__file__).parent
src_dir = api_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
