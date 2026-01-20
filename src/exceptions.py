"""
自定义异常类 - 统一异常体系
"""


class DAASError(Exception):
    """DAAS系统基础异常"""
    pass


class DataError(DAASError):
    """数据相关错误"""
    pass


class DataLoaderError(DataError):
    """数据加载错误"""
    pass


class DataFetchError(DataError):
    """数据获取错误"""
    pass


class DataValidationError(DataError):
    """数据验证错误"""
    pass


class APIError(DataError):
    """API 调用错误"""
    pass


class StrategyError(DAASError):
    """策略相关错误"""
    pass


class FactorError(DAASError):
    """因子计算错误"""
    pass


class ConfigurationError(DAASError):
    """配置错误"""
    pass


class CacheError(DAASError):
    """缓存错误"""
    pass


class ValidationError(DataValidationError):
    """数据验证错误（向后兼容）"""
    pass
