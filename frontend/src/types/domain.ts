/**
 * Domain Types - Business Domain Types
 */
export enum MarketRegime {
  Bull = "Bull",
  Bear = "Bear"
}

export interface StockData {
  date: string;
  price: number;
  bbi: number;
}

export interface HunterResult {
  id: string;
  code: string;
  name: string;
  price: number;
  changePercent: number;
  rps: number;
  volumeRatio: number;
  aiAnalysis: string;
}

export interface PortfolioPosition {
  id: string;
  code: string;
  name: string;
  cost: number;
  currentPrice: number;
  shares: number;
  stopLossPrice: number;
}

export interface BacktestResult {
  date: string;
  strategyEquity: number;
  benchmarkEquity: number;
}

export interface TradeRecord {
  code: string;
  name: string;
  returnPercent: number;
  entryDate: string;
  exitDate: string;
}

export type PageView = 'dashboard' | 'hunter' | 'portfolio' | 'lab';
