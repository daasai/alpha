import { useEffect, useState, useRef, type FC } from 'react';
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Play } from 'lucide-react';
import { useBacktest } from '../../hooks/useLab';
import { useLabStore } from '../../store/labStore';
import { SkeletonChart } from '../common/Loading';
import { useToast } from '../common/Toast';

const Lab: FC = () => {
  const { showToast } = useToast();
  const { backtestResult } = useLabStore();
  const { runBacktest, loading, error } = useBacktest();
  const loadingStartTimeRef = useRef<number | null>(null);
  const [showLongLoadingHint, setShowLongLoadingHint] = useState(false);

  useEffect(() => {
    if (error) {
      const errorMessage = error.message || '回测失败 (Backtest Failed)';
      showToast(errorMessage, 'error');
    }
  }, [error, showToast]);

  useEffect(() => {
    if (loading) {
      loadingStartTimeRef.current = Date.now();
      setShowLongLoadingHint(false);
      // 3秒后显示额外提示
      const timer = setTimeout(() => {
        setShowLongLoadingHint(true);
      }, 3000);
      return () => clearTimeout(timer);
    } else {
      loadingStartTimeRef.current = null;
      setShowLongLoadingHint(false);
    }
  }, [loading]);

  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2023-12-31');
  const [rpsThreshold, setRpsThreshold] = useState(85);
  const [stopLossPct, setStopLossPct] = useState(8.0);
  const [maxPositions, setMaxPositions] = useState(4);

  const handleRunBacktest = () => {
    // 验证日期
    if (new Date(startDate) >= new Date(endDate)) {
      showToast('开始日期必须早于结束日期 (Start date must be earlier than end date)', 'error');
      return;
    }
    
    // 验证参数
    if (stopLossPct < 0 || stopLossPct > 100) {
      showToast('止损百分比必须在0-100之间 (Stop loss percentage must be between 0-100)', 'error');
      return;
    }
    
    if (maxPositions < 1 || maxPositions > 20) {
      showToast('最大持仓数必须在1-20之间 (Max positions must be between 1-20)', 'error');
      return;
    }
    
    const start = startDate.replace(/-/g, '');
    const end = endDate.replace(/-/g, '');
    
    runBacktest({
      start_date: start,
      end_date: end,
      holding_days: 5,
      stop_loss_pct: stopLossPct / 100,
      cost_rate: 0.002,
      benchmark_code: '000300.SH',
      index_code: '000300.SH',
      max_positions: maxPositions,
      rps_threshold: rpsThreshold,
    });
  };

  // 计算年化收益率
  const calculateAnnualizedReturn = (totalReturn: number, startDate: string, endDate: string): number => {
    const days = (new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24);
    if (days <= 0) return 0;
    const annualizedReturn = ((1 + totalReturn / 100) ** (365 / days) - 1) * 100;
    return annualizedReturn;
  };

  // Prepare chart data
  const chartData = backtestResult?.equity_curve?.map(item => ({
    date: item.date,
    strategyEquity: item.strategy_equity,
    benchmarkEquity: item.benchmark_equity,
  })) || [];

  return (
    <div className="grid grid-cols-[25%_75%] h-full overflow-hidden">
      {/* Left Panel: Configuration (25%) */}
      <aside className="sticky top-0 h-screen overflow-y-auto bg-white border-r border-gray-200 p-6 flex flex-col gap-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-1">🧪 实验参数</h2>
          <p className="text-xs text-gray-500">Strategy Wind Tunnel</p>
        </div>

        <div className="flex flex-col gap-6">
          {/* Date Range Picker */}
          <div>
            <label htmlFor="backtest-start-date" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">回测范围 (Backtest Range)</label>
            <div className="flex gap-2">
              <input 
                id="backtest-start-date"
                type="date" 
                className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" 
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <input 
                id="backtest-end-date"
                type="date" 
                className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" 
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
          </div>

          {/* RPS Threshold Slider */}
          <div>
            <label htmlFor="lab-rps-threshold" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">RPS阈值 (RPS Threshold)</label>
            <input 
              id="lab-rps-threshold"
              type="range" 
              min="80"
              max="99"
              step="1"
              value={rpsThreshold}
              onChange={(e) => setRpsThreshold(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black" 
            />
            <div className="flex justify-between items-center mt-1">
              <div className="flex justify-between text-xs text-gray-400 flex-1">
                <span>80</span>
                <span>90</span>
                <span>99</span>
              </div>
            </div>
            <div className="mt-2 text-sm font-semibold text-gray-900">
              当前值 (Current Value): {rpsThreshold}
            </div>
          </div>

          {/* Stop Loss Input */}
          <div>
            <label htmlFor="stop-loss-pct" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">止损比例 (Stop Loss %)</label>
            <input 
              id="stop-loss-pct"
              type="number" 
              step="0.1"
              min="0"
              max="100"
              className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" 
              value={stopLossPct}
              onChange={(e) => setStopLossPct(parseFloat(e.target.value) || 8.0)}
            />
          </div>

          {/* Max Positions Input */}
          <div>
            <label htmlFor="max-positions" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">最大持仓数 (Max Positions)</label>
            <input 
              id="max-positions"
              type="number" 
              min="1"
              max="20"
              className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" 
              value={maxPositions}
              onChange={(e) => setMaxPositions(parseInt(e.target.value) || 4)}
            />
          </div>
        </div>

        <div className="mt-auto">
          <button 
            type="button"
            onClick={handleRunBacktest}
            disabled={loading}
            className="w-full bg-black hover:bg-gray-800 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
          >
            <Play size={18} fill="white" />
            {loading ? '运行中... (Running...)' : '🚀 开始回测 (Run Backtest)'}
          </button>
        </div>
      </aside>

      {/* Right Panel: Results (75%) */}
      <main className="overflow-y-auto bg-gray-50 p-4 md:p-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center min-h-[400px]">
            <SkeletonChart />
            <p className="mt-4 text-gray-600">Simulating Strategy... (This may take a few seconds)</p>
            {showLongLoadingHint && (
              <p className="mt-2 text-sm text-gray-500">回测可能需要更长时间，请耐心等待...</p>
            )}
          </div>
        ) : backtestResult?.success ? (
          <div className="max-w-6xl mx-auto space-y-8">
            
            {/* Equity Curve */}
            <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-100 shadow-sm min-h-[300px] md:min-h-[400px]">
              <h3 className="text-lg font-bold text-gray-900 mb-6">权益曲线 (Equity Curve)</h3>
              {chartData?.length > 0 ? (
                <div className="h-[250px] md:h-[320px] w-full min-h-[250px]">
                  <ResponsiveContainer width="100%" height={320}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 10, fill: '#9ca3af' }} 
                        axisLine={false} 
                        tickLine={false}
                        minTickGap={40}
                      />
                      <YAxis 
                        domain={['auto', 'auto']}
                        tick={{ fontSize: 10, fill: '#9ca3af' }} 
                        axisLine={false} 
                        tickLine={false} 
                        width={35}
                      />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                        formatter={(value: number, name: string) => {
                          if (name === '策略 (Strategy)') {
                            return [`${value.toFixed(4)}`, '策略净值'];
                          } else if (name === '基准 (Benchmark)') {
                            return [`${value.toFixed(4)}`, '基准净值'];
                          }
                          return [value, name];
                        }}
                        labelFormatter={(label: string) => `日期: ${label}`}
                      />
                      <Legend verticalAlign="top" height={36} iconType="circle" />
                      <Line 
                        type="monotone" 
                        dataKey="strategyEquity" 
                        stroke="#EF4444" 
                        strokeWidth={2} 
                        dot={false}
                        name="策略 (Strategy)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="benchmarkEquity" 
                        stroke="#9CA3AF" 
                        strokeWidth={2} 
                        dot={false} 
                        strokeDasharray="5 5"
                        name="基准 (Benchmark)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-[250px] md:h-[320px] flex items-center justify-center text-gray-400">
                  暂无数据 (No Data)
                </div>
              )}
            </div>

            {/* Section A: Key Metrics (KPIs) */}
            {backtestResult.metrics && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  {/* 总收益率 */}
                  <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">总收益率 (Total Return)</div>
                    <div className={`text-2xl font-bold mb-1 ${
                      backtestResult.metrics.total_return > 0 ? 'text-ashare-red' : 'text-gray-900'
                    }`}>
                      {backtestResult.metrics.total_return.toFixed(2)}%
                    </div>
                    {backtestResult.metrics.benchmark_return !== undefined && (
                      <div className={`text-xs font-medium ${
                        (backtestResult.metrics.total_return - backtestResult.metrics.benchmark_return) >= 0 
                          ? 'text-ashare-red' 
                          : 'text-ashare-green'
                      }`}>
                        {backtestResult.metrics.total_return - backtestResult.metrics.benchmark_return >= 0 ? '+' : ''}
                        {(backtestResult.metrics.total_return - backtestResult.metrics.benchmark_return).toFixed(2)}% vs 基准 (vs Benchmark)
                      </div>
                    )}
                  </div>

                  {/* 年化收益率 */}
                  <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">年化收益率 (Annualized Return)</div>
                    <div className={`text-2xl font-bold ${
                      calculateAnnualizedReturn(backtestResult.metrics.total_return, startDate, endDate) > 0 
                        ? 'text-ashare-red' 
                        : 'text-gray-900'
                    }`}>
                      {calculateAnnualizedReturn(backtestResult.metrics.total_return, startDate, endDate).toFixed(2)}%
                    </div>
                  </div>

                  {/* 最大回撤 */}
                  <div className={`p-4 rounded-xl border shadow-sm ${
                    backtestResult.metrics.max_drawdown < -20 
                      ? 'bg-red-50 border-red-200' 
                      : 'bg-white border-gray-100'
                  }`}>
                    <div className={`text-xs font-semibold uppercase tracking-wide mb-2 ${
                      backtestResult.metrics.max_drawdown < -20 ? 'text-red-600' : 'text-gray-500'
                    }`}>
                      最大回撤 (Max Drawdown)
                      {backtestResult.metrics.max_drawdown < -20 && ' ⚠️'}
                    </div>
                    <div className={`text-2xl font-bold mb-1 ${
                      backtestResult.metrics.max_drawdown < -20 ? 'text-red-600' : 'text-gray-900'
                    }`}>
                      {backtestResult.metrics.max_drawdown.toFixed(2)}%
                    </div>
                    {backtestResult.metrics.max_drawdown < -20 && (
                      <div className="text-xs text-red-600 font-medium">风险较高 (High Risk)</div>
                    )}
                  </div>

                  {/* 胜率 */}
                  <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                    <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">胜率 (Win Rate)</div>
                    <div className="text-2xl font-bold text-gray-900">
                      {backtestResult.metrics.win_rate !== undefined && backtestResult.metrics.win_rate !== null
                        ? `${backtestResult.metrics.win_rate.toFixed(2)}%`
                        : 'N/A'}
                    </div>
                  </div>
                </div>

                {/* 总交易数 */}
                {backtestResult.metrics.total_trades !== undefined && backtestResult.metrics.total_trades !== null && (
                  <div className="bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                    <div className="text-sm font-semibold text-gray-700">总交易数 (Total Trades): <span className="text-lg font-bold text-gray-900">{backtestResult.metrics.total_trades}</span></div>
                  </div>
                )}
              </>
            )}

            {/* Section C: Top Contributors */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Winners */}
              <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h4 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span>🏆</span> 最佳/最差交易 - Top 3 盈利股票 (Top 3 Winners)
                </h4>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left">
                      <th className="pb-2 font-medium text-gray-500">股票 (Stock)</th>
                      <th className="pb-2 font-medium text-gray-500 text-right">收益率 (Return %)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {backtestResult.top_winners?.map((trade) => (
                      <tr key={trade.code}>
                        <td className="py-3">
                          <div className="font-medium text-gray-900">{trade.name}</div>
                          <div className="text-xs text-gray-400">{trade.code}</div>
                        </td>
                        <td className="py-3 text-right font-bold text-ashare-red">
                          +{trade.total_gain_pct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Losers */}
              <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h4 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span>💣</span> 最佳/最差交易 - Top 3 亏损股票 (Top 3 Losers)
                </h4>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left">
                      <th className="pb-2 font-medium text-gray-500">股票 (Stock)</th>
                      <th className="pb-2 font-medium text-gray-500 text-right">收益率 (Return %)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {backtestResult.top_losers?.map((trade) => (
                      <tr key={trade.code}>
                        <td className="py-3">
                          <div className="font-medium text-gray-900">{trade.name}</div>
                          <div className="text-xs text-gray-400">{trade.code}</div>
                        </td>
                        <td className={`py-3 text-right font-bold ${
                          trade.total_gain_pct < 0 ? 'text-ashare-green' : 'text-ashare-red'
                        }`}>
                          {trade.total_gain_pct >= 0 ? '+' : ''}{trade.total_gain_pct.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        ) : (
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center text-gray-400">
              <p>Adjust parameters on the left to start.</p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Lab;
