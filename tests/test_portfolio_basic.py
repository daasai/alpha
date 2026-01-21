"""
Basic Portfolio Functionality Test
组合管理基础功能测试
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.database import Account, Position, Order, Base, _engine, _SessionLocal
from src.repositories.portfolio_repository import PortfolioRepository
from api.utils.exceptions import InsufficientFundsError, PositionNotFoundError

def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("组合管理模块基础功能测试")
    print("=" * 60)
    
    repo = PortfolioRepository()
    
    # 1. 测试初始化账户
    print("\n1. 测试初始化账户...")
    account = repo.initialize_account(100000.0)
    # 在会话内访问属性
    cash = account.cash
    total_asset = account.total_asset
    print(f"   ✓ 账户初始化成功: cash={cash}, total_asset={total_asset}")
    
    # 2. 测试获取账户
    print("\n2. 测试获取账户...")
    account2 = repo.get_account()
    if account2:
        cash2 = account2.cash
        total_asset2 = account2.total_asset
        print(f"   ✓ 账户获取成功: cash={cash2}, total_asset={total_asset2}")
    else:
        print("   ✗ 账户获取失败")
        return False
    
    # 3. 测试获取持仓（应该为空）
    print("\n3. 测试获取持仓...")
    positions = repo.get_positions()
    print(f"   ✓ 持仓列表获取成功: 数量={len(positions)}")
    
    # 4. 测试买入订单
    print("\n4. 测试买入订单...")
    try:
        order_data = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        order = repo.create_order(order_data)
        print(f"   ✓ 买入订单创建成功: order_id={order.order_id}, action={order.action}")
        
        # 验证账户资金已扣除
        account_after = repo.get_account()
        expected_cash = 100000.0 - (10.0 * 1000 + 2.0)
        if abs(account_after.cash - expected_cash) < 0.01:
            print(f"   ✓ 账户资金扣除正确: cash={account_after.cash}")
        else:
            print(f"   ✗ 账户资金扣除错误: 期望={expected_cash}, 实际={account_after.cash}")
            return False
        
        # 验证持仓已创建
        position = repo.get_position('000001.SZ')
        if position:
            ts_code = position.ts_code
            total_vol = position.total_vol
            avail_vol = position.avail_vol
            print(f"   ✓ 持仓创建成功: ts_code={ts_code}, total_vol={total_vol}, avail_vol={avail_vol}")
            if avail_vol == 0:
                print(f"   ✓ T+1规则正确: avail_vol=0（当日不可卖出）")
        else:
            print("   ✗ 持仓创建失败")
            return False
            
    except Exception as e:
        print(f"   ✗ 买入订单失败: {e}")
        return False
    
    # 5. 测试资金不足异常
    print("\n5. 测试资金不足异常...")
    try:
        order_data = {
            'trade_date': '20240101',
            'ts_code': '000002.SZ',
            'action': 'BUY',
            'price': 1000.0,  # 高价
            'volume': 1000,
            'fee': 2000.0,
            'name': '测试股票'
        }
        repo.create_order(order_data)
        print("   ✗ 应该抛出资金不足异常")
        return False
    except InsufficientFundsError:
        print("   ✓ 资金不足异常正确抛出")
    except Exception as e:
        print(f"   ✗ 异常类型错误: {e}")
        return False
    
    # 6. 测试卖出订单（需要先设置avail_vol）
    print("\n6. 测试卖出订单...")
    try:
        # 手动设置avail_vol（模拟T+1后）
        from src.database import _SessionLocal
        session = _SessionLocal()
        try:
            position = session.query(Position).filter(Position.ts_code == '000001.SZ').first()
            if position:
                position.avail_vol = position.total_vol
                session.commit()
        finally:
            session.close()
        
        order_data = {
            'trade_date': '20240102',
            'ts_code': '000001.SZ',
            'action': 'SELL',
            'price': 12.0,
            'volume': 500,
            'fee': 1.2,
            'reason': 'test'
        }
        order = repo.create_order(order_data)
        print(f"   ✓ 卖出订单创建成功: order_id={order.order_id}, action={order.action}")
        
        # 验证持仓已更新
        position = repo.get_position('000001.SZ')
        if position:
            total_vol = position.total_vol
            avail_vol = position.avail_vol
            if total_vol == 500 and avail_vol == 500:
                print(f"   ✓ 持仓更新正确: total_vol={total_vol}, avail_vol={avail_vol}")
            else:
                print(f"   ✗ 持仓更新错误: total_vol={total_vol}, avail_vol={avail_vol}")
                return False
        else:
            print("   ✗ 持仓不存在")
            return False
            
    except Exception as e:
        print(f"   ✗ 卖出订单失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 7. 测试持仓不存在异常
    print("\n7. 测试持仓不存在异常...")
    try:
        order_data = {
            'trade_date': '20240102',
            'ts_code': '999999.SH',
            'action': 'SELL',
            'price': 10.0,
            'volume': 100,
            'fee': 0.2
        }
        repo.create_order(order_data)
        print("   ✗ 应该抛出持仓不存在异常")
        return False
    except PositionNotFoundError:
        print("   ✓ 持仓不存在异常正确抛出")
    except Exception as e:
        print(f"   ✗ 异常类型错误: {e}")
        return False
    
    # 8. 测试批量价格更新
    print("\n8. 测试批量价格更新...")
    try:
        prices_dict = {'000001.SZ': 13.0}
        repo.update_positions_market_value(prices_dict)
        
        position = repo.get_position('000001.SZ')
        if position:
            current_price = position.current_price
            profit = position.profit
            profit_pct = position.profit_pct
            if current_price == 13.0:
                print(f"   ✓ 价格更新成功: current_price={current_price}")
                print(f"   ✓ 盈亏计算: profit={profit}, profit_pct={profit_pct:.2f}%")
            else:
                print(f"   ✗ 价格更新失败: current_price={current_price}")
                return False
        else:
            print("   ✗ 持仓不存在")
            return False
        
        # 验证账户市值已更新
        account_final = repo.get_account()
        expected_market_value = 13.0 * 500  # 当前价格 * 持仓数量
        if abs(account_final.market_value - expected_market_value) < 0.01:
            print(f"   ✓ 账户市值更新正确: market_value={account_final.market_value}")
        else:
            print(f"   ✗ 账户市值更新错误: 期望={expected_market_value}, 实际={account_final.market_value}")
            return False
        
        # 验证总资产 = 现金 + 市值
        expected_total_asset = account_final.cash + account_final.market_value
        if abs(account_final.total_asset - expected_total_asset) < 0.01:
            print(f"   ✓ 总资产计算正确: total_asset={account_final.total_asset} = cash({account_final.cash}) + market_value({account_final.market_value})")
        else:
            print(f"   ✗ 总资产计算错误: 期望={expected_total_asset}, 实际={account_final.total_asset}")
            return False
            
    except Exception as e:
        print(f"   ✗ 批量价格更新失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ 所有基础功能测试通过！")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_basic_functionality()
    sys.exit(0 if success else 1)
