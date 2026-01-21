/**
 * Dashboard Store
 * Enhanced version: Integrated with Event Bus for cross-store communication
 */
import { create } from 'zustand';
import type { DashboardOverview, MarketTrend } from '../types/api';
import { eventBus, EventType } from './eventBus';

interface DashboardState {
  overview: DashboardOverview | null;
  marketTrend: MarketTrend | null;
  loading: boolean;
  error: Error | null;
  
  setOverview: (overview: DashboardOverview) => void;
  setMarketTrend: (trend: MarketTrend) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
  refresh: () => void;  // 手动刷新数据
}

export const useDashboardStore = create<DashboardState>((set) => {
  // 监听 Portfolio 更新事件，自动刷新 Dashboard
  eventBus.subscribe('PORTFOLIO_UPDATED', () => {
    // 触发 Dashboard 刷新（实际刷新逻辑在组件中处理）
    set((state) => ({ ...state }));  // 触发状态更新
  });
  
  // 监听市场数据更新事件
  eventBus.subscribe('MARKET_DATA_UPDATED', () => {
    set((state) => ({ ...state }));  // 触发状态更新
  });
  
  return {
    overview: null,
    marketTrend: null,
    loading: false,
    error: null,
    
    setOverview: (overview) => set({ overview }),
    setMarketTrend: (trend) => set({ marketTrend: trend }),
    setLoading: (loading) => set({ loading }),
    setError: (error) => set({ error }),
    
    refresh: () => {
      // 发布刷新事件，触发相关组件刷新
      eventBus.publish('DASHBOARD_REFRESH');
    },
  };
});
