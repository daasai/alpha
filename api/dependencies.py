"""
API Dependencies
"""
from functools import lru_cache
from typing import Generator

from src.config_manager import ConfigManager
from src.data_provider import DataProvider
from src.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache()
def get_config() -> ConfigManager:
    """
    获取配置管理器（单例）
    
    Returns:
        ConfigManager实例
    """
    return ConfigManager()


def get_data_provider() -> Generator[DataProvider, None, None]:
    """
    获取数据提供者（依赖注入）
    
    Yields:
        DataProvider实例
    """
    config = get_config()
    provider = DataProvider()
    try:
        yield provider
    finally:
        # 清理资源（如果需要）
        pass
