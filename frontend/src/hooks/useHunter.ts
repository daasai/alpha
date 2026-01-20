/**
 * Hunter Hooks
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { useApi } from './useApi';
import { useHunterStore } from '../store/hunterStore';
import * as hunterApi from '../api/services/hunter';
import type { HunterScanRequest } from '../types/api';

/**
 * Hook for hunter filters
 */
export function useHunterFilters() {
  const { setFilters } = useHunterStore();
  
  const apiState = useApi(
    () => hunterApi.getFilters().then(res => {
      if (!res.success || !res.data) {
        throw new Error(res.error || res.message || '获取筛选条件失败');
      }
      return res.data;
    }),
    { immediate: true }
  );

  const setFiltersRef = useRef(setFilters);
  
  useEffect(() => {
    setFiltersRef.current = setFilters;
  }, [setFilters]);

  useEffect(() => {
    if (apiState.data) {
      setFiltersRef.current(apiState.data);
    }
  }, [apiState.data]);

  return apiState;
}

/**
 * Hook for hunter scan
 */
export function useHunterScan() {
  const [scanRequest, setScanRequest] = useState<HunterScanRequest | null>(null);
  const scanRequestRef = useRef<HunterScanRequest | null>(null);
  const { setResults, setError } = useHunterStore();
  
  const setResultsRef = useRef(setResults);
  const setErrorRef = useRef(setError);
  
  useEffect(() => {
    setResultsRef.current = setResults;
    setErrorRef.current = setError;
  }, [setResults, setError]);

  // 同步 ref 和 state
  useEffect(() => {
    scanRequestRef.current = scanRequest;
  }, [scanRequest]);
  
  const scanState = useApi(
    () => {
      const currentRequest = scanRequestRef.current;
      if (!currentRequest) {
        throw new Error('Scan request not set');
      }
      return hunterApi.scanStocks(currentRequest).then(res => {
        // 检查外层响应
        if (!res.success) {
          throw new Error(res.error || res.message || '扫描失败');
        }
        
        // 检查data是否存在
        if (!res.data) {
          throw new Error('扫描响应数据为空');
        }
        
        const data = res.data;
        // 检查内层响应
        if (!data.success) {
          throw new Error(data.error || '扫描失败');
        }
        
        // 成功时清除错误状态并设置结果
        setErrorRef.current(null);
        setResultsRef.current(data.results);
        return data;
      });
    },
    { immediate: false }
  );

  const scan = useCallback((request: HunterScanRequest) => {
    scanRequestRef.current = request;
    setScanRequest(request);
    scanState.refetch();
  }, [scanState]);

  return {
    ...scanState,
    scan,
  };
}
