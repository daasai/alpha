#!/usr/bin/env python3
"""
更新账户余额脚本
用于充值或调整账户的现金和总资产
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.repositories.portfolio_repository import PortfolioRepository
from src.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """更新账户余额"""
    repository = PortfolioRepository()
    
    # 目标值
    target_cash = 190215.0
    target_total_asset = 200000.0
    
    try:
        # 检查账户是否存在
        account = repository.get_account()
        if not account:
            logger.warning("账户不存在，正在初始化...")
            account = repository.initialize_account(initial_cash=target_cash)
            # 然后更新总资产
            account = repository.update_account_balance(
                cash=target_cash,
                total_asset=target_total_asset
            )
        else:
            # 更新账户余额
            account = repository.update_account_balance(
                cash=target_cash,
                total_asset=target_total_asset
            )
        
        # 验证结果
        updated_account = repository.get_account()
        if updated_account:
            print("=" * 60)
            print("账户余额更新成功！")
            print("=" * 60)
            print(f"现金余额: ¥{updated_account.cash:,.2f}")
            print(f"总资产:   ¥{updated_account.total_asset:,.2f}")
            print(f"市值:     ¥{updated_account.market_value:,.2f}")
            print(f"冻结资金: ¥{updated_account.frozen_cash:,.2f}")
            print("=" * 60)
            
            # 验证计算
            expected_market_value = target_total_asset - target_cash
            if abs(updated_account.market_value - expected_market_value) < 0.01:
                print("✓ 市值计算正确（总资产 - 现金）")
            else:
                print(f"⚠ 警告：市值计算可能有问题（期望 {expected_market_value:.2f}，实际 {updated_account.market_value:.2f}）")
        else:
            print("❌ 更新后无法获取账户信息")
            return 1
            
    except Exception as e:
        logger.error(f"更新账户余额失败: {e}")
        print(f"❌ 错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
