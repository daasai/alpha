"""
自定义异常类
"""


class DataLoaderError(Exception):
    """数据加载错误"""
    pass


class APIError(DataLoaderError):
    """API 调用错误"""
    pass


class ConfigurationError(Exception):
    """配置错误"""
    pass


class CacheError(Exception):
    """缓存错误"""
    pass


class ValidationError(Exception):
    """数据验证错误"""
    pass
