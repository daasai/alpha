/**
 * Portfolio Hooks
 * Enhanced version: Integrated with Event Bus
 */
import { useEffect, useRef } from 'react';
import { useApi } from './useApi';
import { usePortfolioStore } from '../store/portfolioStore';
import { eventBus } from '../store/eventBus';
import * as portfolioApi from '../api/services/portfolio';
import type { PortfolioPosition, PortfolioMetrics } from '../types/api';

/**
 * Hook for portfolio positions
 */
export function usePortfolioPositions() {
  const { setPositions, setError } = usePortfolioStore();
  
  const apiState = useApi(
    () => portfolioApi.getPositions().then(res => res.data!.positions),
    { immediate: true }
  );

  const setPositionsRef = useRef(setPositions);
  const setErrorRef = useRef(setError);
  
  useEffect(() => {
    setPositionsRef.current = setPositions;
    setErrorRef.current = setError;
  }, [setPositions, setError]);

  useEffect(() => {
    if (apiState.data) {
      setPositionsRef.current(apiState.data);
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
 * Hook for portfolio metrics
 */
export function usePortfolioMetrics() {
  const { setMetrics, setError } = usePortfolioStore();
  
  const apiState = useApi(
    () => portfolioApi.getMetrics().then(res => res.data!.metrics),
    { immediate: true }
  );

  const setMetricsRef = useRef(setMetrics);
  const setErrorRef = useRef(setError);
  
  useEffect(() => {
    setMetricsRef.current = setMetrics;
    setErrorRef.current = setError;
  }, [setMetrics, setError]);

  useEffect(() => {
    if (apiState.data) {
      setMetricsRef.current(apiState.data);
    }
  }, [apiState.data]);

  useEffect(() => {
    if (apiState.error) {
      setErrorRef.current(apiState.error);
    }
  }, [apiState.error]);

  return apiState;
}
