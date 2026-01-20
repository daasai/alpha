/**
 * Portfolio API Service
 */
import apiClient from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  ApiResponse,
  PortfolioPosition,
  PortfolioMetrics,
  AddPositionRequest,
  UpdatePositionRequest,
} from '../../types/api';

/**
 * Get portfolio positions
 */
export const getPositions = async (): Promise<ApiResponse<{ positions: PortfolioPosition[] }>> => {
  const response = await apiClient.get(API_ENDPOINTS.PORTFOLIO_POSITIONS);
  return response as unknown as ApiResponse<{ positions: PortfolioPosition[] }>;
};

/**
 * Get portfolio metrics
 */
export const getMetrics = async (): Promise<ApiResponse<{ metrics: PortfolioMetrics }>> => {
  const response = await apiClient.get(API_ENDPOINTS.PORTFOLIO_METRICS);
  return response as unknown as ApiResponse<{ metrics: PortfolioMetrics }>;
};

/**
 * Add position
 */
export const addPosition = async (
  request: AddPositionRequest
): Promise<ApiResponse<PortfolioPosition>> => {
  const response = await apiClient.post(API_ENDPOINTS.PORTFOLIO_POSITIONS, request);
  return response as unknown as ApiResponse<PortfolioPosition>;
};

/**
 * Update position
 */
export const updatePosition = async (
  positionId: string,
  request: UpdatePositionRequest
): Promise<ApiResponse<PortfolioPosition>> => {
  const response = await apiClient.put(`${API_ENDPOINTS.PORTFOLIO_POSITIONS}/${positionId}`, request);
  return response as unknown as ApiResponse<PortfolioPosition>;
};

/**
 * Delete position
 */
export const deletePosition = async (positionId: string): Promise<void> => {
  await apiClient.delete(`${API_ENDPOINTS.PORTFOLIO_POSITIONS}/${positionId}`);
};

/**
 * Refresh prices
 */
export const refreshPrices = async (): Promise<ApiResponse<{ updated_count: number; total_positions: number }>> => {
  const response = await apiClient.post(API_ENDPOINTS.PORTFOLIO_REFRESH_PRICES);
  return response as unknown as ApiResponse<{ updated_count: number; total_positions: number }>;
};
