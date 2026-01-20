/**
 * Dashboard Hooks
 */
import { useEffect, useRef } from 'react';
import { useApi } from './useApi';
import { useDashboardStore } from '../store/dashboardStore';
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

  return apiState;
}
