/**
 * Error Handler - 统一错误处理工具
 * 提供错误消息映射和错误上报功能
 */

export interface APIError {
  success: false;
  error: string;
  message: string;
  error_id?: string;
  data?: any;
}

/**
 * 错误消息映射（后端错误码 → 用户友好消息）
 */
const ERROR_MESSAGE_MAP: Record<string, string> = {
  'DATA_FETCH_ERROR': '数据获取失败，请稍后重试',
  'DATA_VALIDATION_ERROR': '数据验证失败，请检查输入数据',
  'STRATEGY_ERROR': '策略执行失败，请检查策略配置',
  'FACTOR_ERROR': '因子计算失败，请检查因子配置',
  'CONFIGURATION_ERROR': '配置错误，请检查配置文件',
  'API_ERROR': 'API调用失败，请稍后重试',
  'RATE_LIMIT_ERROR': 'Tushare API访问频率超限，请等待60秒后重试',
  'VALIDATION_ERROR': '请求参数验证失败，请检查输入参数',
  'HTTP_ERROR': '请求处理失败',
  'INTERNAL_ERROR': '服务器内部错误，请稍后重试',
  'UNHANDLED_ERROR': '发生未知错误，请联系技术支持',
  'NETWORK_ERROR': '网络连接失败，请检查网络连接',
};

/**
 * 获取用户友好的错误消息
 */
export function getErrorMessage(error: Error | APIError | unknown): string {
  // 处理 API 错误响应
  if (typeof error === 'object' && error !== null) {
    const apiError = error as APIError;
    if ('error' in apiError && 'message' in apiError) {
      // 优先使用映射的消息
      const mappedMessage = ERROR_MESSAGE_MAP[apiError.error];
      if (mappedMessage) {
        return mappedMessage;
      }
      // 否则使用API返回的消息
      return apiError.message || '操作失败';
    }
  }
  
  // 处理 Error 对象
  if (error instanceof Error) {
    // 检查是否是网络错误
    if ('isNetworkError' in error && (error as any).isNetworkError) {
      return ERROR_MESSAGE_MAP['NETWORK_ERROR'] || '网络连接失败';
    }
    
    // 检查错误代码
    const errorCode = (error as any).code;
    if (errorCode && ERROR_MESSAGE_MAP[errorCode]) {
      return ERROR_MESSAGE_MAP[errorCode];
    }
    
    // 使用错误消息（但过滤技术细节）
    const message = error.message;
    
    // 检测QPS限制错误
    if (message.includes('每分钟最多访问') || 
        message.includes('QPS限制') || 
        message.includes('rate limit') ||
        message.includes('RateLimitError')) {
      return ERROR_MESSAGE_MAP['RATE_LIMIT_ERROR'] || 'Tushare API访问频率超限，请等待60秒后重试';
    }
    
    if (message.includes('Network') || message.includes('network')) {
      return ERROR_MESSAGE_MAP['NETWORK_ERROR'] || '网络连接失败';
    }
    
    return message || '操作失败';
  }
  
  // 默认消息
  return '发生未知错误，请稍后重试';
}

/**
 * 获取错误ID（用于追踪）
 */
export function getErrorId(error: Error | APIError | unknown): string | null {
  if (typeof error === 'object' && error !== null) {
    const apiError = error as APIError;
    if ('error_id' in apiError) {
      return apiError.error_id || null;
    }
  }
  return null;
}

/**
 * 错误上报（可选功能）
 */
export function reportError(
  error: Error | APIError | unknown,
  context?: Record<string, any>
): void {
  const errorMessage = getErrorMessage(error);
  const errorId = getErrorId(error);
  
  // 在开发环境下输出到控制台
  if (import.meta.env.DEV) {
    console.error('Error Report:', {
      message: errorMessage,
      errorId,
      error,
      context,
    });
  }
  
  // 生产环境可以上报到错误监控服务
  // 例如：Sentry, LogRocket 等
  // if (import.meta.env.PROD) {
  //   // 上报到错误监控服务
  // }
}

/**
 * 格式化错误对象用于显示
 */
export function formatErrorForDisplay(
  error: Error | APIError | unknown
): {
  message: string;
  errorId: string | null;
  showDetails: boolean;
} {
  const message = getErrorMessage(error);
  const errorId = getErrorId(error);
  
  // 在开发环境下显示详细信息
  const showDetails = import.meta.env.DEV;
  
  return {
    message,
    errorId,
    showDetails,
  };
}
