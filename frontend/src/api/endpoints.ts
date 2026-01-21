/**
 * API Endpoints
 */
// Use relative path in development (Vite proxy), full URL in production
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  // In development, use relative path to leverage Vite proxy
  if (import.meta.env.DEV) {
    return ''; // Empty string means use current origin, Vite proxy handles /api
  }
  // In production, use default API URL
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

export const API_ENDPOINTS = {
  // Dashboard
  DASHBOARD_OVERVIEW: `${API_BASE_URL}/api/dashboard/overview`,
  DASHBOARD_MARKET_TREND: `${API_BASE_URL}/api/dashboard/market-trend`,
  
  // Hunter
  HUNTER_SCAN: `${API_BASE_URL}/api/hunter/scan`,
  HUNTER_FILTERS: `${API_BASE_URL}/api/hunter/filters`,
  
  // Portfolio
  PORTFOLIO_POSITIONS: `${API_BASE_URL}/api/portfolio/positions`,
  PORTFOLIO_METRICS: `${API_BASE_URL}/api/portfolio/metrics`,
  PORTFOLIO_REFRESH_PRICES: `${API_BASE_URL}/api/portfolio/refresh-prices`,
  PORTFOLIO_OVERVIEW: `${API_BASE_URL}/api/portfolio/overview`,
  PORTFOLIO_HISTORY: `${API_BASE_URL}/api/portfolio/history`,
  PORTFOLIO_ORDER: `${API_BASE_URL}/api/portfolio/order`,
  
  // Lab
  LAB_BACKTEST: `${API_BASE_URL}/api/lab/backtest`,
  
  // Jobs
  JOBS_TRIGGER: `${API_BASE_URL}/api/v1/jobs/daily-runner/trigger`,
  JOBS_STATUS: `${API_BASE_URL}/api/v1/jobs/daily-runner/status`,
  JOBS_HISTORY: `${API_BASE_URL}/api/v1/jobs/daily-runner/history`,
} as const;
