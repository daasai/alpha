/**
 * Hunter Store
 */
import { create } from 'zustand';
import type { HunterStockResult, HunterFilters } from '../types/api';

interface HunterState {
  results: HunterStockResult[];
  filters: HunterFilters | null;
  rpsThreshold: number;
  volumeRatio: number;
  loading: boolean;
  error: Error | null;
  
  setResults: (results: HunterStockResult[]) => void;
  setFilters: (filters: HunterFilters) => void;
  setRpsThreshold: (threshold: number) => void;
  setVolumeRatio: (ratio: number) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const useHunterStore = create<HunterState>((set) => ({
  results: [],
  filters: null,
  rpsThreshold: 85,
  volumeRatio: 1.5,
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
  },
  setRpsThreshold: (threshold) => set({ rpsThreshold: threshold }),
  setVolumeRatio: (ratio) => set({ volumeRatio: ratio }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
