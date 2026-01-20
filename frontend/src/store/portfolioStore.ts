/**
 * Portfolio Store
 */
import { create } from 'zustand';
import type { PortfolioPosition, PortfolioMetrics } from '../types/api';

interface PortfolioState {
  positions: PortfolioPosition[];
  metrics: PortfolioMetrics | null;
  loading: boolean;
  error: Error | null;
  
  setPositions: (positions: PortfolioPosition[]) => void;
  addPosition: (position: PortfolioPosition) => void;
  updatePosition: (id: string, position: Partial<PortfolioPosition>) => void;
  removePosition: (id: string) => void;
  setMetrics: (metrics: PortfolioMetrics) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  positions: [],
  metrics: null,
  loading: false,
  error: null,
  
  setPositions: (positions) => set({ positions }),
  addPosition: (position) => set((state) => ({
    positions: [...state.positions, position]
  })),
  updatePosition: (id, updates) => set((state) => ({
    positions: state.positions.map(pos =>
      pos.id === id ? { ...pos, ...updates } : pos
    )
  })),
  removePosition: (id) => set((state) => ({
    positions: state.positions.filter(pos => pos.id !== id)
  })),
  setMetrics: (metrics) => set({ metrics }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
