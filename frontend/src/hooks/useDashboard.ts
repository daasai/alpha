/**
 * Dashboard Hooks
 * Enhanced version: Integrated with Event Bus for auto-refresh
 */
import { useEffect, useRef } from 'react';
import { useApi } from './useApi';
import { useDashboardStore } from '../store/dashboardStore';
import { eventBus } from '../store/eventBus';
import * as dashboardApi from '../api/services/dashboard';
import type { DashboardOverview, MarketTrend } from '../types/api';

/**
 * Hook for dashboard overview
 */
export function useDashboardOverview(tradeDate?: string) {
  const { setOverview, setError } = useDashboardStore();
  
  const apiState = useApi(
    () => dashboardApi.getDashboardOverview(tradeDate).then(res => res.data!),
    { immediate: true }
  );

  // Use refs to avoid dependency issues with zustand setters
  const setOverviewRef = useRef(setOverview);
  const setErrorRef = useRef(setError);
  
  useEffect(() => {
    setOverviewRef.current = setOverview;
    setErrorRef.current = setError;
  }, [setOverview, setError]);

  useEffect(() => {
    if (apiState.data) {
      setOverviewRef.current(apiState.data);
    }
  }, [apiState.data]);

  useEffect(() => {
    if (apiState.error) {
      setErrorRef.current(apiState.error);
    }
  }, [apiState.error]);

  // 监听 Dashboard 刷新事件
  useEffect(() => {
    const unsubscribe = eventBus.subscribe('DASHBOARD_REFRESH', () => {
      // 触发重新获取数据
      if (apiState.refetch) {
        apiState.refetch();
      }
    });
    
    return unsubscribe;
  }, [apiState]);

  return apiState;
}

/**
 * Hook for market trend
 */
export function useMarketTrend(days: number = 60, indexCode: string = '000001.SH') {
  const { setMarketTrend, setError } = useDashboardStore();
  
  const apiState = useApi(
    () => dashboardApi.getMarketTrend(days, indexCode).then(res => res.data!),
    { immediate: true }
  );

  // Use refs to avoid dependency issues with zustand setters
  const setMarketTrendRef = useRef(setMarketTrend);
  const setErrorRef = useRef(setError);
  
  useEffect(() => {
    setMarketTrendRef.current = setMarketTrend;
    setErrorRef.current = setError;
  }, [setMarketTrend, setError]);

  useEffect(() => {
    if (apiState.data) {
      setMarketTrendRef.current(apiState.data);
    }
  }, [apiState.data]);

  useEffect(() => {
    if (apiState.error) {
      setErrorRef.current(apiState.error);
    }
  }, [apiState.error]);

  // 监听市场数据更新事件
  useEffect(() => {
    const unsubscribe = eventBus.subscribe('MARKET_DATA_UPDATED', () => {
      // 触发重新获取数据
      if (apiState.refetch) {
        apiState.refetch();
      }
    });
    
    return unsubscribe;
  }, [apiState]);

  return apiState;
}
