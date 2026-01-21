/**
 * Hunter Store
 */
import { create } from 'zustand';
import type { StockSignal, HunterFilters } from '../types/api';

interface HunterState {
  results: StockSignal[];
  filters: HunterFilters | null;
  rpsThreshold: number;
  volumeRatio: number;
  tradeDate: string | null;
  loading: boolean;
  error: Error | null;
  
  setResults: (results: StockSignal[]) => void;
  setFilters: (filters: HunterFilters) => void;
  setRpsThreshold: (threshold: number) => void;
  setVolumeRatio: (ratio: number) => void;
  setTradeDate: (date: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const useHunterStore = create<HunterState>((set) => ({
  results: [],
  filters: null,
  rpsThreshold: 85,
  volumeRatio: 1.5,
  tradeDate: null,
  loading: false,
  error: null,
  
  setResults: (results) => set({ results }),
  setFilters: (filters) => {
    set({ filters });
    // Update default values
    if (filters.rps_threshold) {
      set({ rpsThreshold: filters.rps_threshold.default });
    }
    if (filters.volume_ratio_threshold) {
      set({ volumeRatio: filters.volume_ratio_threshold.default });
    }
    // Set default trade date (first available date or current date)
    if (filters.available_dates && filters.available_dates.length > 0) {
      set({ tradeDate: filters.available_dates[0].value });
    }
  },
  setRpsThreshold: (threshold) => set({ rpsThreshold: threshold }),
  setVolumeRatio: (ratio) => set({ volumeRatio: ratio }),
  setTradeDate: (date) => set({ tradeDate: date }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
