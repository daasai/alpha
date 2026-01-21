import { useState } from 'react';
import type React from 'react';
import { MOCK_BACKTEST_DATA, MOCK_WINNERS, MOCK_LOSERS } from '../constants';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { Play } from 'lucide-react';

// AI测试评估动画组件
const AITestingAnimation: React.FC = () => {
  return (
    <div className="flex flex-col items-center justify-center h-full w-full">
      <div className="relative w-32 h-32 mb-6">
        {/* 外圈旋转动画 */}
        <div className="absolute inset-0 border-4 border-gray-200 border-t-gray-900 rounded-full animate-spin"></div>
        {/* 内圈反向旋转 */}
        <div className="absolute inset-4 border-4 border-gray-300 border-b-gray-900 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
        {/* 中心AI图标 */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-2xl font-bold text-gray-900">AI</div>
        </div>
      </div>
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-gray-700">Simulating Strategy...</p>
        <p className="text-xs text-gray-500">AI测试评估中 (This may take a few seconds)</p>
        <p className="text-xs text-gray-400 mt-2">回测可能需要更长时间, 请耐心等待...</p>
      </div>
    </div>
  );
};

const Lab: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [backtestData, setBacktestData] = useState<typeof MOCK_BACKTEST_DATA | null>(null);

  const handleRunBacktest = () => {
    setIsLoading(true);
    setBacktestData(null);
    // 模拟异步加载
    setTimeout(() => {
      setBacktestData(MOCK_BACKTEST_DATA);
      setIsLoading(false);
    }, 2000);
  };

  return (
    <div className="flex flex-col md:flex-row h-full overflow-hidden">
      {/* Sidebar Controls (Inner) */}
      <div className="w-full md:w-80 bg-white border-b md:border-b-0 md:border-r border-gray-200 p-6 flex flex-col gap-6 md:gap-8 overflow-y-auto shrink-0 h-auto md:h-full">
        <div>
          <h2 className="text-xl font-bold text-gray-900 mb-1">🧪 实验室</h2>
          <p className="text-xs text-gray-500">Strategy Wind Tunnel</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-1 gap-4 md:gap-6">
          <div className="col-span-2 md:col-span-1">
            <fieldset>
              <legend className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Backtest Range</legend>
              <div className="flex gap-2">
                <input type="date" id="start-date" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue="2023-01-01" />
                <input type="date" id="end-date" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue="2023-12-31" />
              </div>
            </fieldset>
          </div>

          <div className="col-span-2 md:col-span-1">
            <label htmlFor="rps-threshold" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">RPS Threshold</label>
            <input type="range" id="rps-threshold" className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black" />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>80</span>
              <span>90</span>
              <span>99</span>
            </div>
          </div>

          <div>
             <label htmlFor="stop-loss" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Stop Loss (%)</label>
             <input type="number" id="stop-loss" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue={8} />
          </div>

          <div>
             <label htmlFor="max-position" className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Max Position (%)</label>
             <input type="number" id="max-position" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue={25} />
          </div>
        </div>

        <div className="mt-4 md:mt-auto">
          <button 
            type="button"
            onClick={handleRunBacktest}
            disabled={isLoading}
            className="w-full bg-black hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95"
          >
            <Play size={18} fill="white" />
            {isLoading ? '运行中...' : '运行回测 (Run)'}
          </button>
        </div>
      </div>

      {/* Main Results Area */}
      <div className="flex-1 bg-gray-50 p-4 md:p-8 overflow-y-auto">
        <div className="max-w-6xl mx-auto space-y-8">
          
          {/* Equity Curve */}
          <div className="bg-white p-4 md:p-6 rounded-xl border border-gray-100 shadow-sm min-h-[300px] md:min-h-[400px]">
            <h3 className="text-lg font-bold text-gray-900 mb-6">Equity Curve</h3>
            <div className="h-[250px] md:h-[320px] w-full">
              {isLoading || !backtestData ? (
                <div className="w-full h-full flex items-center justify-center px-4">
                  <div className="w-full max-w-4xl h-full flex items-center justify-center">
                    <AITestingAnimation />
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={backtestData}>
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
                    />
                    <Legend 
                      verticalAlign="top" 
                      height={36} 
                      iconType="circle"
                      wrapperStyle={{ fontSize: '11px', lineHeight: '14px' }}
                      iconSize={10}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="strategyEquity" 
                      stroke="#EF4444" 
                      strokeWidth={2} 
                      dot={false}
                      name="Strategy"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="benchmarkEquity" 
                      stroke="#9CA3AF" 
                      strokeWidth={2} 
                      dot={false} 
                      strokeDasharray="4 4"
                      name="Benchmark"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Attribution: Top Winners vs Top Losers */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Winners */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
              <h4 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>🏆</span> Top 3 Winners
              </h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-2 font-medium text-gray-500">Asset</th>
                    <th className="pb-2 font-medium text-gray-500 text-right">Return</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {MOCK_WINNERS.map((trade) => (
                    <tr key={trade.code}>
                      <td className="py-3">
                        <div className="font-medium text-gray-900">{trade.name}</div>
                        <div className="text-xs text-gray-400">{trade.code}</div>
                      </td>
                      <td className="py-3 text-right font-bold text-ashare-red">
                        +{trade.returnPercent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Losers */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
              <h4 className="text-sm font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>💣</span> Top 3 Losers
              </h4>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="pb-2 font-medium text-gray-500">Asset</th>
                    <th className="pb-2 font-medium text-gray-500 text-right">Return</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {MOCK_LOSERS.map((trade) => (
                    <tr key={trade.code}>
                      <td className="py-3">
                        <div className="font-medium text-gray-900">{trade.name}</div>
                        <div className="text-xs text-gray-400">{trade.code}</div>
                      </td>
                      <td className="py-3 text-right font-bold text-ashare-green">
                        {trade.returnPercent}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Lab;