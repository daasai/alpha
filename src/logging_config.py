"""
Logging Configuration Module
统一的日志系统配置
"""

import logging
import sys
from pathlib import Path


def setup_logging(log_level='INFO', log_file=None):
    """
    配置统一日志系统
    
    Args:
        log_level: 日志级别 ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        log_file: 日志文件路径（可选）
    
    Returns:
        logging.RootLogger: 配置好的根日志记录器
    """
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除已有的处理器（避免重复添加）
    root_logger.handlers.clear()
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件输出（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    return root_logger


def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 模块名称
    
    Returns:
        logging.Logger: 日志记录器
    """
    return logging.getLogger(name)
