import React from 'react';
import { MOCK_PORTFOLIO } from '../constants';
import { AlertTriangle, TrendingUp, TrendingDown, Activity } from 'lucide-react';

const Portfolio: React.FC = () => {
  return (
    <div className="p-4 md:p-8 h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-6 md:space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">💼 模拟盘 (Portfolio)</h2>
            <p className="text-gray-500 text-sm mt-1">Real-time position tracking</p>
          </div>
        </div>

        {/* Top Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
          <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
             <div className="absolute top-0 right-0 p-4 opacity-5">
               <TrendingUp size={100} />
             </div>
             <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Total Return</p>
             <h3 className="text-3xl font-bold text-ashare-red flex items-baseline gap-2">
               +18.4%
               <span className="text-sm font-medium text-gray-400 bg-gray-100 px-2 rounded-md">YTD</span>
             </h3>
          </div>
          
          <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
             <div className="absolute top-0 right-0 p-4 opacity-5">
               <TrendingDown size={100} />
             </div>
             <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Max Drawdown</p>
             <h3 className="text-3xl font-bold text-ashare-green">-5.2%</h3>
          </div>

          <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
             <div className="absolute top-0 right-0 p-4 opacity-5">
               <Activity size={100} />
             </div>
             <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Sharpe Ratio</p>
             <h3 className="text-3xl font-bold text-gray-900">2.45</h3>
          </div>
        </div>

        {/* Holdings Table */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left min-w-[700px]">
              <thead className="bg-gray-50/50">
                <tr>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">Asset</th>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Cost</th>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Price</th>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">P&L (%)</th>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Market Value</th>
                  <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">Dist. to SL</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {MOCK_PORTFOLIO.map((pos) => {
                  const pl = (pos.currentPrice - pos.cost) / pos.cost * 100;
                  const marketValue = pos.currentPrice * pos.shares;
                  const distToSl = ((pos.currentPrice - pos.stopLossPrice) / pos.currentPrice) * 100;
                  const isNearStopLoss = distToSl < 2;

                  const plColor = pl > 0 ? 'text-ashare-red' : 'text-ashare-green';
                  const plSign = pl > 0 ? '+' : '';

                  return (
                    <tr 
                      key={pos.id} 
                      className={`
                        transition-colors hover:bg-gray-50
                        ${isNearStopLoss ? 'bg-warning/10' : ''}
                      `}
                    >
                      <td className="py-4 px-6">
                        <div className="font-bold text-gray-900">{pos.name}</div>
                        <div className="text-xs text-gray-400 font-mono">{pos.code}</div>
                      </td>
                      <td className="py-4 px-6 text-right font-mono text-gray-600">{pos.cost.toFixed(2)}</td>
                      <td className="py-4 px-6 text-right font-mono text-gray-900 font-medium">{pos.currentPrice.toFixed(2)}</td>
                      <td className={`py-4 px-6 text-right font-mono font-bold ${plColor}`}>
                        {plSign}{pl.toFixed(2)}%
                      </td>
                      <td className="py-4 px-6 text-right font-mono text-gray-900">
                        ¥{marketValue.toLocaleString()}
                      </td>
                      <td className="py-4 px-6 text-right">
                        {isNearStopLoss ? (
                          <div className="inline-flex items-center gap-1 text-warning font-bold text-sm">
                            <AlertTriangle size={14} />
                            {distToSl.toFixed(1)}%
                          </div>
                        ) : (
                          <span className="text-gray-400 font-mono">{distToSl.toFixed(1)}%</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;