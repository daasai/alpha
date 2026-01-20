/**
 * Lab Store
 */
import { create } from 'zustand';
import type { BacktestResponse, BacktestRequest } from '../types/api';

interface LabState {
  backtestResult: BacktestResponse | null;
  backtestRequest: BacktestRequest | null;
  loading: boolean;
  error: Error | null;
  
  setBacktestResult: (result: BacktestResponse) => void;
  setBacktestRequest: (request: BacktestRequest) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
}

export const useLabStore = create<LabState>((set) => ({
  backtestResult: null,
  backtestRequest: null,
  loading: false,
  error: null,
  
  setBacktestResult: (result) => set({ backtestResult: result }),
  setBacktestRequest: (request) => set({ backtestRequest: request }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
