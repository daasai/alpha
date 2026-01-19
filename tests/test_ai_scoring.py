#!/usr/bin/env python3
"""
AI评分接口测试程序

用于验证 analyze_sentiment 函数是否正常工作。
测试场景：
1. 基本功能测试（单只股票）
2. 多只股票批量测试
3. 空DataFrame处理
4. AI评分连通性和准确性测试（使用模拟数据，跳过真实API调用）

使用方法：
    python3 -m tests.test_ai_scoring
    或
    python3 tests/test_ai_scoring.py
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
load_dotenv()

# 导入项目模块
from src.logging_config import setup_logging, get_logger
from src.monitor import analyze_sentiment
from src.data_provider import DataProvider

# 设置日志
setup_logging(log_level="DEBUG", log_file=None)
logger = get_logger(__name__)


def check_environment():
    """检查环境变量配置"""
    print("=" * 60)
    print("环境检查")
    print("=" * 60)
    
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    tushare_token = os.getenv("TUSHARE_TOKEN")
    
    print(f"OPENAI_API_KEY: {'已设置' if api_key else '❌ 未设置'}")
    print(f"OPENAI_API_BASE: {api_base or '默认(OpenAI官方)'}")
    print(f"OPENAI_MODEL: {model}")
    print(f"TUSHARE_TOKEN: {'已设置' if tushare_token else '❌ 未设置'}")
    print()
    
    if not api_key:
        print("❌ 错误: OPENAI_API_KEY 未设置，请在 .env 文件中配置")
        return False
    
    if not tushare_token:
        print("⚠️  警告: TUSHARE_TOKEN 未设置，可能影响公告获取")
    
    return True


def test_single_stock():
    """测试单只股票的AI评分"""
    print("=" * 60)
    print("测试场景 1: 单只股票评分")
    print("=" * 60)
    
    try:
        # 创建测试数据
        test_df = pd.DataFrame({
            "ts_code": ["000001.SZ"],
            "name": ["平安银行"],
            "trade_date": ["20260116"]
        })
        
        print(f"测试股票: {test_df.iloc[0]['name']} ({test_df.iloc[0]['ts_code']})")
        print()
        
        # 初始化DataProvider
        try:
            dp = DataProvider()
            print("✓ DataProvider 初始化成功")
        except ValueError as e:
            print(f"⚠️  DataProvider 初始化失败: {e}")
            print("   将使用 None，analyze_sentiment 会自行创建")
            dp = None
        
        # 调用AI评分
        print("正在调用AI评分接口...")
        result_df = analyze_sentiment(test_df, data_provider=dp)
        
        # 显示结果
        print()
        print("✓ AI评分完成")
        print("-" * 60)
        for idx, row in result_df.iterrows():
            print(f"股票代码: {row['ts_code']}")
            print(f"股票名称: {row['name']}")
            print(f"AI评分: {row['ai_score']}")
            print(f"评分理由: {row['ai_reason']}")
            print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_stocks():
    """测试多只股票的批量AI评分"""
    print()
    print("=" * 60)
    print("测试场景 2: 多只股票批量评分")
    print("=" * 60)
    
    try:
        # 创建测试数据（使用一些常见的股票代码）
        test_stocks = [
            {"ts_code": "000001.SZ", "name": "平安银行"},
            {"ts_code": "000002.SZ", "name": "万科A"},
            {"ts_code": "600000.SH", "name": "浦发银行"},
        ]
        
        test_df = pd.DataFrame(test_stocks)
        test_df["trade_date"] = "20260116"
        
        print(f"测试股票数量: {len(test_df)}")
        for _, row in test_df.iterrows():
            print(f"  - {row['name']} ({row['ts_code']})")
        print()
        
        # 初始化DataProvider
        try:
            dp = DataProvider()
            print("✓ DataProvider 初始化成功")
        except ValueError as e:
            print(f"⚠️  DataProvider 初始化失败: {e}")
            dp = None
        
        # 调用AI评分
        print("正在调用AI评分接口（批量处理）...")
        result_df = analyze_sentiment(test_df, data_provider=dp)
        
        # 显示结果
        print()
        print("✓ 批量AI评分完成")
        print("-" * 60)
        print(f"{'股票代码':<15} {'股票名称':<15} {'AI评分':<10} {'评分理由':<30}")
        print("-" * 60)
        for idx, row in result_df.iterrows():
            reason_preview = row['ai_reason'][:30] + "..." if len(row['ai_reason']) > 30 else row['ai_reason']
            print(f"{row['ts_code']:<15} {row['name']:<15} {row['ai_score']:<10} {reason_preview:<30}")
        print("-" * 60)
        
        # 统计信息
        print()
        print("统计信息:")
        print(f"  总股票数: {len(result_df)}")
        print(f"  平均评分: {result_df['ai_score'].mean():.2f}")
        print(f"  最高评分: {result_df['ai_score'].max()}")
        print(f"  最低评分: {result_df['ai_score'].min()}")
        print(f"  评分范围: [{result_df['ai_score'].min()}, {result_df['ai_score'].max()}]")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_empty_dataframe():
    """测试空DataFrame的处理"""
    print()
    print("=" * 60)
    print("测试场景 3: 空DataFrame处理")
    print("=" * 60)
    
    try:
        empty_df = pd.DataFrame(columns=["ts_code", "name", "trade_date"])
        print("测试空DataFrame...")
        
        result_df = analyze_sentiment(empty_df)
        
        if result_df.empty:
            print("✓ 正确处理空DataFrame，返回空结果")
            return True
        else:
            print("❌ 空DataFrame应该返回空结果")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_ai_scoring_with_mock_data():
    """测试AI评分（使用模拟数据，跳过真实API调用）"""
    print()
    print("=" * 60)
    print("测试场景 4: AI评分连通性和准确性测试（模拟数据）")
    print("=" * 60)
    
    try:
        # 创建测试数据
        test_stocks = [
            {
                "ts_code": "000001.SZ",
                "name": "平安银行",
                "trade_date": "20260116"
            },
            {
                "ts_code": "000002.SZ",
                "name": "万科A",
                "trade_date": "20260116"
            },
            {
                "ts_code": "600000.SH",
                "name": "浦发银行",
                "trade_date": "20260116"
            },
        ]
        
        test_df = pd.DataFrame(test_stocks)
        
        print(f"测试股票数量: {len(test_df)}")
        for _, row in test_df.iterrows():
            print(f"  - {row['name']} ({row['ts_code']})")
        print()
        
        # 创建模拟的公告数据
        # 包含正面、负面、中性等不同类型的公告
        mock_notices_data = {
            "000001.SZ": pd.DataFrame({
                "ts_code": ["000001.SZ"],
                "ann_date": [datetime.now().strftime("%Y%m%d")],
                "title": ["关于公司业绩预增的公告"],
                "title_ch": ["关于公司业绩预增的公告"],
                "art_code": ["ART001"],
                "column_names": ["业绩预告"]
            }),
            "000002.SZ": pd.DataFrame({
                "ts_code": ["000002.SZ"],
                "ann_date": [datetime.now().strftime("%Y%m%d")],
                "title": ["关于公司收到立案调查通知的公告"],
                "title_ch": ["关于公司收到立案调查通知的公告"],
                "art_code": ["ART002"],
                "column_names": ["风险提示"]
            }),
            "600000.SH": pd.DataFrame({
                "ts_code": ["600000.SH"],
                "ann_date": [datetime.now().strftime("%Y%m%d")],
                "title": ["关于公司回购股份的公告"],
                "title_ch": ["关于公司回购股份的公告"],
                "art_code": ["ART003"],
                "column_names": ["股份变动"]
            }),
        }
        
        # 创建Mock DataProvider
        mock_dp = Mock(spec=DataProvider)
        
        def mock_get_notices(ts_codes, start_date, end_date):
            """模拟get_notices方法"""
            results = []
            for ts_code in ts_codes:
                if ts_code in mock_notices_data:
                    results.append(mock_notices_data[ts_code])
            if results:
                return pd.concat(results, ignore_index=True)
            return pd.DataFrame(columns=["ts_code", "ann_date", "title", "title_ch", "art_code", "column_names"])
        
        mock_dp.get_notices = Mock(side_effect=mock_get_notices)
        
        print("✓ 模拟DataProvider创建成功")
        print("  使用模拟公告数据，跳过真实API调用")
        print()
        
        # 显示模拟的公告数据
        print("模拟公告数据:")
        for ts_code, notice_df in mock_notices_data.items():
            if not notice_df.empty:
                notice = notice_df.iloc[0]
                print(f"  {ts_code}: {notice.get('column_names', '')} - {notice.get('title', '')}")
        print()
        
        # 调用AI评分
        print("正在调用AI评分接口（使用模拟数据）...")
        result_df = analyze_sentiment(test_df, data_provider=mock_dp)
        
        # 验证结果
        print()
        print("✓ AI评分完成")
        print("-" * 60)
        print(f"{'股票代码':<15} {'股票名称':<15} {'AI评分':<10} {'评分理由':<40}")
        print("-" * 60)
        
        all_valid = True
        for idx, row in result_df.iterrows():
            ts_code = row['ts_code']
            name = row['name']
            score = row['ai_score']
            reason = row['ai_reason']
            
            # 验证评分范围
            if not (-10 <= score <= 10):
                print(f"⚠️  {ts_code} 评分超出范围: {score} (应在-10到10之间)")
                all_valid = False
            
            # 验证理由不为空
            if not reason or reason.strip() == "":
                print(f"⚠️  {ts_code} 评分理由为空")
                all_valid = False
            
            reason_preview = reason[:40] + "..." if len(reason) > 40 else reason
            print(f"{ts_code:<15} {name:<15} {score:<10} {reason_preview:<40}")
        
        print("-" * 60)
        
        # 统计信息
        print()
        print("统计信息:")
        print(f"  总股票数: {len(result_df)}")
        print(f"  平均评分: {result_df['ai_score'].mean():.2f}")
        print(f"  最高评分: {result_df['ai_score'].max()}")
        print(f"  最低评分: {result_df['ai_score'].min()}")
        print(f"  评分范围: [{result_df['ai_score'].min()}, {result_df['ai_score'].max()}]")
        
        # 验证连通性：所有股票都应该有评分
        if len(result_df) == len(test_df):
            print("✓ 连通性验证通过：所有股票都获得了AI评分")
        else:
            print(f"❌ 连通性验证失败：期望{len(test_df)}只股票，实际{len(result_df)}只")
            all_valid = False
        
        # 验证准确性：评分应该在合理范围内
        if all(-10 <= score <= 10 for score in result_df['ai_score']):
            print("✓ 准确性验证通过：所有评分都在-10到10的合理范围内")
        else:
            print("❌ 准确性验证失败：存在超出范围的评分")
            all_valid = False
        
        # 验证理由完整性
        if all(reason and reason.strip() for reason in result_df['ai_reason']):
            print("✓ 理由完整性验证通过：所有评分都有理由说明")
        else:
            print("❌ 理由完整性验证失败：存在空的评分理由")
            all_valid = False
        
        return all_valid
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "AI评分接口测试程序" + " " * 23 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请先配置必要的环境变量")
        sys.exit(1)
    
    print()
    
    # 运行测试
    results = []
    
    # 测试1: 单只股票
    results.append(("单只股票评分", test_single_stock()))
    
    # 测试2: 多只股票批量评分
    results.append(("多只股票批量评分", test_multiple_stocks()))
    
    # 测试3: 空DataFrame处理
    results.append(("空DataFrame处理", test_empty_dataframe()))
    
    # 测试4: AI评分连通性和准确性（模拟数据）
    results.append(("AI评分连通性和准确性（模拟数据）", test_ai_scoring_with_mock_data()))
    
    # 显示测试总结
    print()
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    for test_name, passed in results:
        status = "✓ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    print()
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    print(f"总计: {passed_count}/{total_count} 测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
