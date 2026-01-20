/**
 * Hunter API Service
 */
import apiClient from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  ApiResponse,
  HunterScanRequest,
  HunterScanResponse,
  HunterFilters,
} from '../../types/api';

/**
 * Run hunter scan
 */
export const scanStocks = async (
  request: HunterScanRequest
): Promise<ApiResponse<HunterScanResponse>> => {
  const response = await apiClient.post(API_ENDPOINTS.HUNTER_SCAN, request);
  return response as unknown as ApiResponse<HunterScanResponse>;
};

/**
 * Get available filters
 */
export const getFilters = async (): Promise<ApiResponse<HunterFilters>> => {
  const response = await apiClient.get(API_ENDPOINTS.HUNTER_FILTERS);
  return response as unknown as ApiResponse<HunterFilters>;
};
