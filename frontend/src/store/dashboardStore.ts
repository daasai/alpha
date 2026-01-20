/**
 * Dashboard Store
 */
import { create } from 'zustand';
import type { DashboardOverview, MarketTrend } from '../types/api';

interface DashboardState {
  overview: DashboardOverview | null;
  marketTrend: MarketTrend | null;
  loading: boolean;
  error: Error | null;
  
  setOverview: (overview: DashboardOverview) => void;
  setMarketTrend: (trend: MarketTrend) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  overview: null,
  marketTrend: null,
  loading: false,
  error: null,
  
  setOverview: (overview) => set({ overview }),
  setMarketTrend: (trend) => set({ marketTrend: trend }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
