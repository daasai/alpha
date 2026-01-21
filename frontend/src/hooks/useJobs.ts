/**
 * Jobs Hooks
 */
import { useState, useCallback, useEffect } from 'react';
import * as jobsApi from '../api/services/jobs';
import type { TriggerRequest, ExecutionStatus, ExecutionHistory } from '../api/services/jobs';

/**
 * Hook for triggering daily runner
 */
export function useTriggerDailyRunner() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [data, setData] = useState<jobsApi.TriggerResponse | null>(null);

  const trigger = useCallback(async (request: TriggerRequest = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await jobsApi.triggerDailyRunner(request);
      
      if (response.success && response.data) {
        setData(response.data);
        return response.data;
      } else {
        const errorMsg = response.message || response.error || '触发任务失败';
        throw new Error(errorMsg);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('触发任务失败');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    trigger,
    loading,
    error,
    data
  };
}

/**
 * Hook for getting daily runner status
 */
export function useDailyRunnerStatus(trade_date?: string, autoRefresh: boolean = false) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [status, setStatus] = useState<ExecutionStatus | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await jobsApi.getDailyRunnerStatus(trade_date);
      
      if (response.success && response.data) {
        setStatus(response.data);
        return response.data;
      } else {
        const errorMsg = response.message || response.error || '获取状态失败';
        throw new Error(errorMsg);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('获取状态失败');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [trade_date]);

  useEffect(() => {
    fetchStatus();
    
    if (autoRefresh) {
      const interval = setInterval(fetchStatus, 5000); // 每5秒刷新一次
      return () => clearInterval(interval);
    }
  }, [fetchStatus, autoRefresh]);

  return {
    status,
    loading,
    error,
    refetch: fetchStatus
  };
}

/**
 * Hook for getting daily runner history
 */
export function useDailyRunnerHistory(
  trade_date?: string,
  status?: string,
  limit: number = 50
) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [history, setHistory] = useState<ExecutionHistory | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await jobsApi.getDailyRunnerHistory(trade_date, status, limit);
      
      if (response.success && response.data) {
        setHistory(response.data);
        return response.data;
      } else {
        const errorMsg = response.message || response.error || '获取历史失败';
        throw new Error(errorMsg);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('获取历史失败');
      setError(error);
      return null;
    } finally {
      setLoading(false);
    }
  }, [trade_date, status, limit]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return {
    history,
    loading,
    error,
    refetch: fetchHistory
  };
}

/**
 * Hook for retrying failed execution
 */
export function useRetryExecution() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const retry = useCallback(async (execution_id: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await jobsApi.retryExecution(execution_id);
      
      if (response.success && response.data) {
        return response.data;
      } else {
        const errorMsg = response.message || response.error || '重试任务失败';
        throw new Error(errorMsg);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('重试任务失败');
      setError(error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    retry,
    loading,
    error
  };
}
