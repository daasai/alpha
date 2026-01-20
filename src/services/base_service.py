"""
Base Service - 基础服务类
所有服务的基类，提供通用功能
"""

from typing import Optional
from ..config_manager import ConfigManager
from ..data_provider import DataProvider
from ..logging_config import get_logger

logger = get_logger(__name__)


class BaseService:
    """
    基础服务类，提供通用功能
    
    所有Service的基类，提供数据提供者和配置管理器的统一初始化。
    支持依赖注入，便于测试和扩展。
    """
    
    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        config: Optional[ConfigManager] = None
    ) -> None:
        """
        初始化基础服务
        
        Args:
            data_provider: 数据提供者实例，如果为None则创建新实例
            config: 配置管理器实例，如果为None则创建新实例
            
        Note:
            如果data_provider或config为None，会自动创建新实例。
            这允许服务既可以独立使用，也可以接受依赖注入。
        """
        if data_provider is None:
            from ..data_provider import DataProvider
            self.data_provider: DataProvider = DataProvider()
        else:
            self.data_provider = data_provider
        
        if config is None:
            from ..config_manager import ConfigManager
            self.config: ConfigManager = ConfigManager()
        else:
            self.config = config
        
        logger.debug(f"{self.__class__.__name__} 初始化完成")
