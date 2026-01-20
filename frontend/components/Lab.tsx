import React from 'react';
import { MOCK_BACKTEST_DATA, MOCK_WINNERS, MOCK_LOSERS } from '../constants';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { Play } from 'lucide-react';

const Lab: React.FC = () => {
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
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Backtest Range</label>
            <div className="flex gap-2">
              <input type="date" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue="2023-01-01" />
              <input type="date" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue="2023-12-31" />
            </div>
          </div>

          <div className="col-span-2 md:col-span-1">
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">RPS Threshold</label>
            <input type="range" className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black" />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>80</span>
              <span>90</span>
              <span>99</span>
            </div>
          </div>

          <div>
             <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Stop Loss (%)</label>
             <input type="number" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue={8} />
          </div>

          <div>
             <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide block mb-2">Max Position (%)</label>
             <input type="number" className="w-full text-sm border border-gray-200 rounded p-2 bg-gray-50" defaultValue={25} />
          </div>
        </div>

        <div className="mt-4 md:mt-auto">
          <button className="w-full bg-black hover:bg-gray-800 text-white font-bold py-3 px-4 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95">
            <Play size={18} fill="white" />
            运行回测 (Run)
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
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={MOCK_BACKTEST_DATA}>
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
                  <Legend verticalAlign="top" height={36} iconType="circle" />
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
                  {MOCK_WINNERS.map((trade, i) => (
                    <tr key={i}>
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
                  {MOCK_LOSERS.map((trade, i) => (
                    <tr key={i}>
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