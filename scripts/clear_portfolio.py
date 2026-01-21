#!/usr/bin/env python3
"""
清空模拟盘全部数据脚本
"""
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.repositories.portfolio_repository import PortfolioRepository
from src.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """清空所有模拟盘持仓"""
    parser = argparse.ArgumentParser(description="清空模拟盘全部数据")
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='跳过确认，直接执行清空操作'
    )
    args = parser.parse_args()
    
    print("=" * 50)
    print("清空模拟盘全部数据")
    print("=" * 50)
    
    repository = PortfolioRepository()
    
    # 先查看当前持仓数量
    positions = repository.get_all()
    current_count = len(positions)
    
    if current_count == 0:
        print("当前没有持仓数据，无需清空。")
        return
    
    print(f"\n当前持仓数量: {current_count}")
    
    # 确认操作（除非使用 --yes 参数）
    if not args.yes:
        try:
            confirm = input("\n确认要清空所有持仓数据吗？(yes/no): ").strip().lower()
            if confirm not in ['yes', 'y']:
                print("操作已取消。")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n操作已取消。")
            return
    else:
        print("\n使用 --yes 参数，跳过确认直接执行...")
    
    # 执行清空
    try:
        deleted_count = repository.delete_all()
        print(f"\n✓ 成功清空所有持仓数据，共删除 {deleted_count} 条记录。")
    except Exception as e:
        logger.exception("清空持仓数据失败")
        print(f"\n✗ 清空失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
