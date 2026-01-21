"""
Base API Client - 抽象基类
提供重试机制、限流、错误处理等通用功能
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
import time
import functools
from datetime import datetime, timedelta

import pandas as pd

from ...logging_config import get_logger
from ...config_manager import ConfigManager

logger = get_logger(__name__)


class BaseAPIClient(ABC):
    """API 客户端基类"""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """
        初始化 API 客户端
        
        Args:
            config: 配置管理器，如果为 None 则创建新实例
        """
        if config is None:
            self.config = ConfigManager()
        else:
            self.config = config
        
        # 从配置读取限流参数
        self._request_delay = self.config.get('api_rate_limit.tushare_delay', 0.1)
        self._max_retries = self.config.get('api_rate_limit.max_retries', 3)
        self._retry_delay = self.config.get('api_rate_limit.retry_delay', 0.5)
        self._request_timeout = self.config.get('api.request_timeout', 10)
        
        # 限流：记录最后一次请求时间
        self._last_request_time: Optional[datetime] = None
    
    def _rate_limit(self, delay: Optional[float] = None):
        """
        实现请求限流
        
        Args:
            delay: 延迟时间（秒），如果为 None 则使用配置的默认值
        """
        if delay is None:
            delay = self._request_delay
        
        if self._last_request_time is not None:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < delay:
                sleep_time = delay - elapsed
                time.sleep(sleep_time)
        
        self._last_request_time = datetime.now()
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """
        检测是否是速率限制错误
        
        Args:
            error: 异常对象
            
        Returns:
            是否是速率限制错误
        """
        error_str = str(error).lower()
        # 检测Tushare QPS限制错误的关键词
        rate_limit_keywords = [
            '每分钟最多访问',
            'qps',
            'rate limit',
            'too many requests',
            '429'
        ]
        return any(keyword in error_str for keyword in rate_limit_keywords)
    
    def _retry_on_failure(
        self,
        func: Callable,
        max_retries: Optional[int] = None,
        retry_delay: Optional[float] = None,
        exceptions: tuple = (Exception,)
    ) -> Any:
        """
        重试机制装饰器
        
        Args:
            func: 要执行的函数
            max_retries: 最大重试次数，如果为 None 则使用配置的默认值
            retry_delay: 重试延迟（秒），如果为 None 则使用配置的默认值
            exceptions: 需要重试的异常类型元组
            
        Returns:
            函数执行结果
            
        Raises:
            最后一次尝试的异常或RateLimitError
        """
        from ...exceptions import RateLimitError
        
        if max_retries is None:
            max_retries = self._max_retries
        if retry_delay is None:
            retry_delay = self._retry_delay
        
        # QPS限制的重试延迟（秒）
        qps_retry_delay = self.config.get('api_rate_limit.qps_retry_delay', 60)
        
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except exceptions as e:
                last_exception = e
                
                # 检测是否是QPS限制错误
                if self._is_rate_limit_error(e):
                    if attempt < max_retries - 1:
                        # QPS限制：使用更长的延迟时间
                        wait_time = qps_retry_delay
                        logger.warning(
                            f"检测到QPS限制错误 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}，"
                            f"{wait_time} 秒后重试..."
                        )
                        time.sleep(wait_time)
                    else:
                        # 所有重试都失败，抛出RateLimitError
                        logger.error(f"QPS限制错误，已重试 {max_retries} 次: {str(e)[:200]}")
                        raise RateLimitError(
                            message=f"Tushare API QPS限制：{str(e)}",
                            retry_after=qps_retry_delay,
                            cause=e
                        ) from e
                else:
                    # 普通错误：使用递增延迟
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)  # 递增延迟
                        logger.debug(
                            f"API 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)[:100]}，"
                            f"{wait_time:.2f} 秒后重试..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"API 调用失败 (已重试 {max_retries} 次): {str(e)[:200]}")
        
        # 所有重试都失败，抛出最后一次异常
        raise last_exception
    
    @abstractmethod
    def get_data(self, **kwargs) -> pd.DataFrame:
        """
        获取数据（抽象方法，子类必须实现）
        
        Args:
            **kwargs: 数据获取参数
            
        Returns:
            DataFrame: 获取的数据
        """
        pass
    
    def _handle_error(self, error: Exception, context: dict = None) -> None:
        """
        处理错误（可被子类重写）
        
        Args:
            error: 异常对象
            context: 上下文信息
        """
        context_str = f", 上下文: {context}" if context else ""
        logger.error(f"API 调用错误: {str(error)}{context_str}")
