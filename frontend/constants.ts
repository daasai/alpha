import { BacktestResult, HunterResult, MarketRegime, PortfolioPosition, StockData, TradeRecord } from "./types";

// Mock Data for Dashboard Chart
export const generateMarketData = (): StockData[] => {
  const data: StockData[] = [];
  let price = 3000;
  let bbi = 2950;
  
  for (let i = 0; i < 90; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (90 - i));
    
    const change = (Math.random() - 0.48) * 30; // Slight upward bias
    price += change;
    bbi = bbi * 0.95 + price * 0.05; // Simple moving average-ish smoothing

    data.push({
      date: date.toISOString().split('T')[0],
      price: Math.round(price),
      bbi: Math.round(bbi),
    });
  }
  return data;
};

export const MOCK_MARKET_DATA = generateMarketData();

// Mock Data for Hunter
export const MOCK_HUNTER_RESULTS: HunterResult[] = [
  { id: '1', code: '600519', name: '贵州茅台', price: 1750.20, changePercent: 1.25, rps: 92, volumeRatio: 1.5, aiAnalysis: "白酒龙头，现金流充沛，估值回归合理区间，北向资金持续流入。" },
  { id: '2', code: '300750', name: '宁德时代', price: 185.50, changePercent: -0.85, rps: 88, volumeRatio: 2.1, aiAnalysis: "动力电池行业竞争加剧，但海外市场份额扩张超预期，关注技术面支撑。" },
  { id: '3', code: '002594', name: '比亚迪', price: 240.10, changePercent: 2.30, rps: 95, volumeRatio: 3.2, aiAnalysis: "销量持续创新高，高端车型利润释放，均线多头排列，量价齐升。" },
  { id: '4', code: '601318', name: '中国平安', price: 45.30, changePercent: 0.15, rps: 65, volumeRatio: 0.8, aiAnalysis: "保险业务复苏缓慢，地产风险敞口可控，股息率具备吸引力。" },
  { id: '5', code: '688111', name: '金山办公', price: 280.00, changePercent: 5.40, rps: 98, volumeRatio: 4.5, aiAnalysis: "AI+办公落地速度加快，付费用户增长强劲，机构资金大幅抢筹。" },
  { id: '6', code: '000001', name: '平安银行', price: 10.45, changePercent: -1.20, rps: 45, volumeRatio: 0.9, aiAnalysis: "零售银行业务承压，息差收窄，短期缺乏明显催化剂。" },
  { id: '7', code: '600036', name: '招商银行', price: 32.10, changePercent: 0.50, rps: 70, volumeRatio: 1.1, aiAnalysis: "基本面稳健，也是防御性配置首选之一。" },
];

// Mock Data for Portfolio
export const MOCK_PORTFOLIO: PortfolioPosition[] = [
  { id: 'p1', code: '300750', name: '宁德时代', cost: 175.00, currentPrice: 185.50, shares: 500, stopLossPrice: 165.00 },
  { id: 'p2', code: '600519', name: '贵州茅台', cost: 1800.00, currentPrice: 1750.20, shares: 100, stopLossPrice: 1700.00 }, // Loss
  { id: 'p3', code: '002594', name: '比亚迪', cost: 210.00, currentPrice: 240.10, shares: 300, stopLossPrice: 236.00 }, // Close to stop loss (simulated context)
];

// Mock Data for Backtest
export const generateBacktestData = (): BacktestResult[] => {
  const data: BacktestResult[] = [];
  let strategy = 100000;
  let benchmark = 100000;
  
  for (let i = 0; i < 180; i++) {
    const date = new Date();
    date.setDate(date.getDate() - (180 - i));
    
    strategy *= (1 + (Math.random() - 0.4) * 0.03); // More volatility
    benchmark *= (1 + (Math.random() - 0.45) * 0.02); // Less return

    data.push({
      date: date.toISOString().split('T')[0],
      strategyEquity: Math.round(strategy),
      benchmarkEquity: Math.round(benchmark),
    });
  }
  return data;
};

export const MOCK_BACKTEST_DATA = generateBacktestData();

export const MOCK_WINNERS: TradeRecord[] = [
  { code: '300418', name: '昆仑万维', returnPercent: 45.2, entryDate: '2024-01-10', exitDate: '2024-02-15' },
  { code: '002230', name: '科大讯飞', returnPercent: 32.8, entryDate: '2024-02-01', exitDate: '2024-03-01' },
  { code: '603019', name: '中科曙光', returnPercent: 28.5, entryDate: '2024-01-20', exitDate: '2024-02-28' },
];

export const MOCK_LOSERS: TradeRecord[] = [
  { code: '601888', name: '中国中免', returnPercent: -15.4, entryDate: '2024-01-05', exitDate: '2024-01-25' },
  { code: '000725', name: '京东方A', returnPercent: -8.2, entryDate: '2024-02-10', exitDate: '2024-02-20' },
  { code: '601012', name: '隆基绿能', returnPercent: -6.5, entryDate: '2024-03-01', exitDate: '2024-03-15' },
];
