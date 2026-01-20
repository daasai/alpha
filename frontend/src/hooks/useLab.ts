/**
 * Lab Hooks
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { useApi } from './useApi';
import { useLabStore } from '../store/labStore';
import * as labApi from '../api/services/lab';
import type { BacktestRequest } from '../types/api';

/**
 * Hook for backtest
 */
export function useBacktest() {
  const [backtestRequest, setBacktestRequest] = useState<BacktestRequest | null>(null);
  const backtestRequestRef = useRef<BacktestRequest | null>(null);
  const { setBacktestResult } = useLabStore();
  
  const setBacktestResultRef = useRef(setBacktestResult);
  
  useEffect(() => {
    setBacktestResultRef.current = setBacktestResult;
  }, [setBacktestResult]);

  // 同步 ref 和 state
  useEffect(() => {
    backtestRequestRef.current = backtestRequest;
  }, [backtestRequest]);
  
  const backtestState = useApi(
    () => {
      const currentRequest = backtestRequestRef.current;
      if (!currentRequest) {
        throw new Error('Backtest request not set');
      }
      return labApi.runBacktest(currentRequest).then(res => {
        // 检查外层响应
        if (!res.success) {
          const errorMsg = res.message || res.error || '回测失败';
          throw new Error(typeof errorMsg === 'string' ? errorMsg : '回测失败');
        }
        
        // 检查data是否存在
        if (!res.data) {
          throw new Error('回测响应数据为空');
        }
        
        const data = res.data;
        // 检查内层响应
        if (!data.success) {
          const errorMsg = data.error || '回测失败';
          throw new Error(typeof errorMsg === 'string' ? errorMsg : '回测失败');
        }
        
        setBacktestResultRef.current(data);
        return data;
      }).catch(err => {
        // 确保错误消息是字符串
        const errorMessage = err instanceof Error ? err.message : String(err || '回测失败');
        throw new Error(errorMessage);
      });
    },
    { immediate: false }
  );

  const runBacktest = useCallback((request: BacktestRequest) => {
    backtestRequestRef.current = request;
    setBacktestRequest(request);
    backtestState.refetch();
  }, [backtestState]);

  return {
    ...backtestState,
    runBacktest,
  };
}
