#!/usr/bin/env python3
"""
Daily Runner Cron Script - Cron执行脚本

用于cron调度的独立脚本，支持命令行参数和日志输出
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# 确保项目根目录在 Python 路径中
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from src.jobs.task_executor import TaskExecutor
from src.jobs.notification_service import NotificationService
from src.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Daily Runner Cron Script')
    parser.add_argument(
        '--trade-date',
        type=str,
        help='交易日期（YYYYMMDD格式），如果不提供则使用当前日期'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='强制执行（绕过幂等性检查）'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='日志文件路径（可选）'
    )
    
    args = parser.parse_args()
    
    # 设置日志文件（如果指定）
    if args.log_file:
        import logging
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logger.addHandler(file_handler)
    
    try:
        # 创建任务执行器
        task_executor = TaskExecutor()
        notification_service = NotificationService()
        
        # 执行任务
        logger.info(f"开始执行每日任务 (cron触发)")
        logger.info(f"参数: trade_date={args.trade_date}, force={args.force}")
        
        result = task_executor.execute(
            trade_date=args.trade_date,
            trigger_type='SCHEDULED',
            force=args.force
        )
        
        # 发送通知
        notification_service.notify_execution_result(
            execution_id=result.get('execution_id', ''),
            trade_date=result.get('trade_date', ''),
            status=result.get('status', 'FAILED'),
            errors=result.get('errors', []),
            duration_seconds=result.get('duration_seconds')
        )
        
        # 输出结果
        if result.get('success'):
            logger.info(f"任务执行成功: execution_id={result.get('execution_id')}")
            sys.exit(0)
        else:
            logger.error(f"任务执行失败: execution_id={result.get('execution_id')}, errors={result.get('errors')}")
            sys.exit(1)
    
    except Exception as e:
        logger.exception(f"执行任务异常: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
