"""
配置管理模块
"""

import yaml
from pathlib import Path
from typing import Any, Optional
from .logging_config import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = 'config/settings.yaml'):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        if not self.config_path.exists():
            logger.error(f"配置文件不存在: {self.config_path}")
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        logger.debug(f"配置加载完成: {self.config_path}")
        logger.debug(f"配置内容: {self.config}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项（支持点号分隔的嵌套键，如 'api.use_free_api'）
        
        Args:
            key: 配置键（支持点号分隔，如 'api.use_free_api'）
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            
            if value is None:
                logger.warning(f"配置项 {key} 值为 None，使用默认值: {default}")
                return default
            
            return value
        except (KeyError, TypeError):
            logger.warning(f"配置项 {key} 不存在，使用默认值: {default}")
            return default
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        logger.info("配置已重新加载")
