/**
 * API Types
 */

/**
 * Standard API Response
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Paginated Response
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * Dashboard API Types
 */
export interface DashboardOverview {
  market_regime: {
    regime: string;
    is_bull: boolean;
  };
  sentiment: {
    sentiment: number;
    change?: number;
  };
  target_position: {
    position: number;
    label: string;
  };
  portfolio_nav: {
    nav: number;
    change_percent?: number;
  };
}

export interface MarketTrendDataPoint {
  date: string;
  price: number;
  bbi: number;
}

export interface MarketTrend {
  index_code: string;
  index_name: string;
  data: MarketTrendDataPoint[];
}

/**
 * Hunter API Types
 */
export interface HunterScanRequest {
  trade_date?: string;
  rps_threshold?: number;
  volume_ratio_threshold?: number;
}

export interface StockSignal {
  code: string;
  name: string;
  price: number;
  rps: number;
  volume_ratio: number;
  pe?: number;
  industry?: string;
  reason?: string;
}

export interface HunterStockResult {
  id: string;
  code: string;
  name: string;
  price: number;
  change_percent: number;
  rps: number;
  volume_ratio: number;
  pe?: number;
  industry?: string;
  reason?: string;
  ai_analysis?: string;
}

export interface HunterScanResponse {
  success: boolean;
  trade_date?: string;
  results: StockSignal[];
  diagnostics?: any;
  error?: string;
}

export interface TradeDateOption {
  value: string;
  label: string;
}

export interface HunterFilters {
  rps_threshold: {
    default: number;
    min: number;
    max: number;
    step: number;
  };
  volume_ratio_threshold: {
    default: number;
    min: number;
    max: number;
    step: number;
  };
  pe_max: {
    default: number;
    min: number;
    max: number;
    step: number;
  };
  available_dates?: TradeDateOption[];
}

/**
 * Portfolio API Types
 */
export interface Account {
  id: number;
  total_asset: number;
  cash: number;
  market_value: number;
  frozen_cash: number;
  initial_asset?: number;
  yesterday_nav?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Order {
  order_id: string;
  trade_date: string;
  ts_code: string;
  action: 'BUY' | 'SELL';
  price: number;
  volume: number;
  fee: number;
  status: string;
  strategy_tag?: string;
  reason?: string;
  created_at?: string;
}

export interface OrderParams {
  action: 'BUY' | 'SELL';
  ts_code: string;
  price: number;
  volume: number;
  strategy_tag?: string;
  reason?: string;
}

export interface PortfolioPosition {
  id: string;
  code: string;
  name: string;
  cost?: number;
  current_price?: number;
  shares?: number;
  stop_loss_price?: number;
  total_vol?: number;
  avail_vol?: number;
  profit?: number;
  profit_pct?: number;
}

export interface PortfolioMetrics {
  total_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
}

export interface PortfolioOverview {
  account: Account;
  positions: PortfolioPosition[];
}

export interface AddPositionRequest {
  code: string;
  name: string;
  cost: number;
  shares: number;
  stop_loss_price: number;
}

export interface UpdatePositionRequest {
  cost?: number;
  shares?: number;
  stop_loss_price?: number;
}

/**
 * Lab API Types
 */
export interface BacktestRequest {
  start_date: string;
  end_date: string;
  holding_days?: number;
  stop_loss_pct?: number;
  cost_rate?: number;
  benchmark_code?: string;
  index_code?: string;
  max_positions?: number;
  rps_threshold?: number;
}

export interface EquityCurvePoint {
  date: string;
  strategy_equity: number;
  benchmark_equity: number;
}

export interface TopContributor {
  code: string;
  name: string;
  total_gain: number;
  total_gain_pct: number;
}

export interface BacktestMetrics {
  total_return: number;
  benchmark_return: number;
  max_drawdown: number;
  win_rate?: number;
  sharpe_ratio?: number;
  total_trades?: number;
}

export interface BacktestResponse {
  success: boolean;
  metrics?: BacktestMetrics;
  equity_curve: EquityCurvePoint[];
  top_winners: TopContributor[];
  top_losers: TopContributor[];
  error?: string;
}
