"""
API Dependencies
"""
from functools import lru_cache
from typing import Generator

from src.config_manager import ConfigManager
from src.data_provider import DataProvider
from src.api.clients import TushareClient, EastmoneyClient
from src.cache import CacheManager
from src.repositories.portfolio_repository import PortfolioRepository
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


@lru_cache()
def get_cache_manager() -> CacheManager:
    """
    获取缓存管理器（单例）
    
    Returns:
        CacheManager实例
    """
    config = get_config()
    return CacheManager(config=config)


@lru_cache()
def get_tushare_client() -> TushareClient:
    """
    获取 Tushare 客户端（单例）
    
    Returns:
        TushareClient实例
    """
    config = get_config()
    return TushareClient(config=config)


@lru_cache()
def get_eastmoney_client() -> EastmoneyClient:
    """
    获取东方财富客户端（单例）
    
    Returns:
        EastmoneyClient实例
    """
    config = get_config()
    return EastmoneyClient(config=config)


def get_data_provider() -> Generator[DataProvider, None, None]:
    """
    获取数据提供者（依赖注入）
    
    Yields:
        DataProvider实例
    """
    config = get_config()
    cache_manager = get_cache_manager()
    tushare_client = get_tushare_client()
    eastmoney_client = get_eastmoney_client()
    
    provider = DataProvider(
        tushare_client=tushare_client,
        eastmoney_client=eastmoney_client,
        cache_manager=cache_manager,
        config=config
    )
    try:
        yield provider
    finally:
        # 清理资源（如果需要）
        pass


def get_portfolio_repository() -> PortfolioRepository:
    """
    获取 PortfolioRepository（单例）
    
    Returns:
        PortfolioRepository实例
    """
    return PortfolioRepository()
