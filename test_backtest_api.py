#!/usr/bin/env python3
"""
测试回测API功能
"""
import requests
import json
from datetime import datetime, timedelta

API_BASE_URL = "http://localhost:8000"

def test_backtest_api():
    """测试回测API"""
    url = f"{API_BASE_URL}/api/lab/backtest"
    
    # 准备测试数据
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    payload = {
        "start_date": start_date.strftime("%Y%m%d"),
        "end_date": end_date.strftime("%Y%m%d"),
        "holding_days": 5,
        "stop_loss_pct": 0.08,
        "cost_rate": 0.002,
        "benchmark_code": "000300.SH",
        "index_code": "000300.SH",
        "max_positions": 4
    }
    
    print("=" * 60)
    print("测试回测API")
    print("=" * 60)
    print(f"请求URL: {url}")
    print(f"请求参数: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, timeout=300)
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get("success"):
                result = data.get("data", {})
                if result.get("success"):
                    print("\n✅ 回测成功!")
                    metrics = result.get("metrics", {})
                    print(f"总收益率: {metrics.get('total_return', 0):.2f}%")
                    print(f"基准收益率: {metrics.get('benchmark_return', 0):.2f}%")
                    print(f"最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
                    equity_curve = result.get("equity_curve", [])
                    print(f"权益曲线点数: {len(equity_curve)}")
                else:
                    print(f"\n❌ 回测失败: {result.get('error', '未知错误')}")
            else:
                print(f"\n❌ API调用失败: {data.get('error', '未知错误')}")
                print(f"错误消息: {data.get('message', '无消息')}")
        else:
            print(f"\n❌ HTTP错误: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误信息: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应内容: {response.text}")
                
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时（超过5分钟）")
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接错误，请确保API服务正在运行")
    except Exception as e:
        print(f"\n❌ 异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backtest_api()
