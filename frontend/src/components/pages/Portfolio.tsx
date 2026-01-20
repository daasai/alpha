import React, { useEffect } from 'react';
import { AlertTriangle, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { usePortfolioPositions, usePortfolioMetrics } from '../../hooks/usePortfolio';
import { usePortfolioStore } from '../../store/portfolioStore';
import { SkeletonCard } from '../common/Loading';
import { useToast } from '../common/Toast';

const Portfolio: React.FC = () => {
  const { showToast } = useToast();
  const { positions, metrics } = usePortfolioStore();
  
  const { loading: positionsLoading, error: positionsError } = usePortfolioPositions();
  const { loading: metricsLoading, error: metricsError } = usePortfolioMetrics();

  useEffect(() => {
    if (positionsError) {
      showToast('获取持仓失败', 'error');
    }
  }, [positionsError, showToast]);

  useEffect(() => {
    if (metricsError) {
      showToast('获取组合指标失败', 'error');
    }
  }, [metricsError, showToast]);

  const isLoading = positionsLoading || metricsLoading;

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
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
            {[1, 2, 3].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <TrendingUp size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Total Return</p>
               <h3 className={`text-3xl font-bold flex items-baseline gap-2 ${(metrics?.total_return || 0) > 0 ? 'text-ashare-red' : 'text-ashare-green'}`}>
                 {(metrics?.total_return || 0) > 0 ? '+' : ''}{metrics?.total_return?.toFixed(1) || '0.0'}%
                 <span className="text-sm font-medium text-gray-400 bg-gray-100 px-2 rounded-md">YTD</span>
               </h3>
            </div>
            
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <TrendingDown size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Max Drawdown</p>
               <h3 className="text-3xl font-bold text-ashare-green">
                 -{metrics?.max_drawdown?.toFixed(1) || '0.0'}%
               </h3>
            </div>

            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <Activity size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Sharpe Ratio</p>
               <h3 className="text-3xl font-bold text-gray-900">
                 {metrics?.sharpe_ratio?.toFixed(2) || '0.00'}
               </h3>
            </div>
          </div>
        )}

        {/* Holdings Table */}
        {isLoading ? (
          <SkeletonCard className="min-h-[400px]" />
        ) : (
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
                  {positions.map((pos) => {
                    const pl = (pos.current_price - pos.cost) / pos.cost * 100;
                    const marketValue = pos.current_price * pos.shares;
                    const distToSl = ((pos.current_price - pos.stop_loss_price) / pos.current_price) * 100;
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
                        <td className="py-4 px-6 text-right font-mono text-gray-900 font-medium">{pos.current_price.toFixed(2)}</td>
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
              {positions.length === 0 && (
                <div className="p-8 text-center text-gray-400">
                  当前无持仓
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Portfolio;
