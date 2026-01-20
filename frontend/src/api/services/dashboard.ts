/**
 * Dashboard API Service
 */
import apiClient from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type { ApiResponse, DashboardOverview, MarketTrend } from '../../types/api';

/**
 * Get dashboard overview
 */
export const getDashboardOverview = async (tradeDate?: string): Promise<ApiResponse<DashboardOverview>> => {
  const params = tradeDate ? { trade_date: tradeDate } : {};
  const response = await apiClient.get(API_ENDPOINTS.DASHBOARD_OVERVIEW, { params });
  return response as unknown as ApiResponse<DashboardOverview>;
};

/**
 * Get market trend data
 */
export const getMarketTrend = async (
  days: number = 60,
  indexCode: string = '000001.SH'
): Promise<ApiResponse<MarketTrend>> => {
  const params = { days, index_code: indexCode };
  const response = await apiClient.get(API_ENDPOINTS.DASHBOARD_MARKET_TREND, { params });
  return response as unknown as ApiResponse<MarketTrend>;
};
