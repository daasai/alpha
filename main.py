"""
Main Entry Point - Alpha MVP Phase 1
程序入口，执行完整的选股和监控流程
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from src.data_loader import DataLoader
from src.strategy import StockStrategy
from src.monitor import AnnouncementMonitor
from src.reporter import ReportGenerator
from src.config_manager import ConfigManager
from src.logging_config import setup_logging, get_logger


def get_trade_date(date_str=None):
    """
    确定交易日期（如果是周末则自动前推至上一个交易日）
    
    Args:
        date_str: 日期字符串，格式 'YYYYMMDD'，如果为 None 则使用今天
        
    Returns:
        str: 交易日期，格式 'YYYYMMDD'
    """
    if date_str:
        date_obj = datetime.strptime(date_str, '%Y%m%d')
    else:
        date_obj = datetime.now()
    
    # 如果是周末，前推到上一个交易日
    # 周六(5) -> 周五, 周日(6) -> 周五
    while date_obj.weekday() >= 5:  # 5=Saturday, 6=Sunday
        date_obj -= timedelta(days=1)
    
    return date_obj.strftime('%Y%m%d')


def main():
    """主执行流程"""
    # 初始化日志系统（先不设置文件，等配置加载后再设置）
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("Alpha MVP Phase 1 - 量化选股系统启动")
    logger.info("=" * 60)
    
    total_steps = 9
    
    def print_step(step_num, message):
        """打印步骤信息，带进度百分比"""
        progress = int((step_num / total_steps) * 100)
        logger.info(f"[{step_num}/{total_steps}] ({progress}%) {message}")
    
    try:
        # 1. 加载配置
        print_step(1, "加载配置...")
        config_manager = ConfigManager()
        
        # 从配置中获取日志设置
        log_level = config_manager.get('logging.level', 'INFO')
        log_file = config_manager.get('logging.file', None)
        if log_file:
            setup_logging(log_level=log_level, log_file=log_file)
        else:
            setup_logging(log_level=log_level)
        
        logger.info("配置加载完成")
        
        # 2. 确定日期
        print_step(2, "确定交易日期...")
        trade_date = get_trade_date()
        logger.info(f"交易日期: {trade_date}")
        
        # 3. 初始化数据加载器
        print_step(3, "初始化数据加载器...")
        # 从配置中获取API设置
        use_free_api = config_manager.get('api.use_free_api', True)
        use_api_abstraction = config_manager.get('api.use_abstraction', False)  # 默认不使用抽象层以保持兼容
        logger.info(f"API配置: 使用 {'免费API' if use_free_api else 'Tushare Pro'}, 抽象层: {use_api_abstraction}")
        data_loader = DataLoader(use_free_api=use_free_api, use_api_abstraction=use_api_abstraction)
        logger.info("数据加载器初始化完成")
        
        # 4. 获取全市场数据
        print_step(4, "获取全市场数据...")
        logger.info("获取股票基本信息...")
        stock_basics = data_loader.get_stock_basics()
        logger.info(f"共获取 {len(stock_basics)} 只股票")
        
        logger.info("获取每日基本面指标...")
        daily_indicators = data_loader.get_daily_indicators(trade_date)
        logger.info(f"共获取 {len(daily_indicators)} 条指标数据")
        
        logger.info("获取财务指标（此步骤较耗时，请耐心等待）...")
        # 传入股票列表以优化性能，只获取已有股票的财务数据
        stock_codes = stock_basics['ts_code'].tolist()
        financial_indicators = data_loader.get_financial_indicators(trade_date, stock_list=stock_codes)
        logger.info(f"共获取 {len(financial_indicators)} 条财务数据")
        
        # 5. 执行选股策略
        print_step(5, "执行选股策略...")
        strategy = StockStrategy()
        anchor_pool = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        logger.info(f"筛选出 {len(anchor_pool)} 只白名单股票")
        
        if anchor_pool.empty:
            logger.warning("未筛选出任何符合条件的股票！")
            return
        
        # 6. 保存白名单到 CSV
        print_step(6, "保存白名单到 CSV...")
        output_dir = Path(config_manager.get('output.directory', 'data/output'))
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_encoding = config_manager.get('output.csv_encoding', 'utf-8-sig')
        csv_filename = output_dir / f"{trade_date}_anchor_pool.csv"
        anchor_pool.to_csv(csv_filename, index=False, encoding=csv_encoding)
        logger.info(f"已保存至: {csv_filename}")
        
        # 7. 获取白名单股票的公告
        print_step(7, "获取白名单股票公告（此步骤较耗时，请耐心等待）...")
        stock_list = anchor_pool['ts_code'].tolist()
        start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=3)).strftime('%Y%m%d')
        # 使用免费API（从配置中读取）
        if use_free_api:
            notices = data_loader.get_notices_free(stock_list, start_date)
        else:
            notices = data_loader.get_notices(stock_list, start_date)
        logger.info(f"共获取 {len(notices)} 条公告")
        
        # 8. 分析公告
        print_step(8, "分析公告异动...")
        monitor = AnnouncementMonitor()
        notice_results = monitor.analyze_notices(notices, lookback_days=3)
        logger.info(f"发现 {len(notice_results)} 条重要异动公告")
        
        # 9. 生成报告
        print_step(9, "生成分析报告...")
        reporter = ReportGenerator(output_dir=str(output_dir))
        report_path = reporter.generate_report(anchor_pool, notice_results, trade_date)
        logger.info(f"报告已生成: {report_path}")
        
        # 完成
        logger.info("\n" + "=" * 60)
        logger.info("任务完成，报告已生成")
        logger.info("=" * 60)
        logger.info(f"白名单股票数量: {len(anchor_pool)}")
        logger.info(f"重要异动公告: {len(notice_results)} 条")
        logger.info(f"报告路径: {report_path}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
