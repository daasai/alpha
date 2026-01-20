/**
 * Lab API Service
 */
import apiClient from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  ApiResponse,
  BacktestRequest,
  BacktestResponse,
} from '../../types/api';

/**
 * Run backtest
 */
export const runBacktest = async (
  request: BacktestRequest
): Promise<ApiResponse<BacktestResponse>> => {
  const response = await apiClient.post(API_ENDPOINTS.LAB_BACKTEST, request);
  return response as unknown as ApiResponse<BacktestResponse>;
};
