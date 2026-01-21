import { useEffect, useState } from 'react';
import type React from 'react';
import { TrendingUp, TrendingDown, Activity, ChevronDown, ChevronUp, BarChart3 } from 'lucide-react';
import { usePortfolioStore } from '../../store/portfolioStore';
import { SkeletonCard } from '../common/Loading';
import { useToast } from '../common/Toast';
import SellOrderModal from '../common/SellOrderModal';
import type { PortfolioPosition } from '../../types/api';

/**
 * 格式化货币显示，小数部分使用小号字体
 */
const formatCurrency = (value: number): { integer: string; decimal: string } => {
  const formatted = value.toLocaleString('zh-CN', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  });
  const parts = formatted.split('.');
  return {
    integer: parts[0],
    decimal: parts[1] ? `.${parts[1]}` : ''
  };
};

const Portfolio: React.FC = () => {
  const { showToast } = useToast();
  const { 
    positions, 
    account, 
    orders, 
    loading, 
    error,
    fetchPortfolio 
  } = usePortfolioStore();
  
  // 计算日盈亏
  const dailyPnL = positions.reduce((sum, pos) => {
    const cost = pos.cost ?? pos.avg_price ?? 0;
    const currentPrice = pos.current_price ?? 0;
    const shares = pos.shares ?? pos.total_vol ?? 0;
    if (cost > 0 && currentPrice > 0) {
      return sum + (currentPrice - cost) * shares;
    }
    return sum;
  }, 0);
  const [sellModalPosition, setSellModalPosition] = useState<PortfolioPosition | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  useEffect(() => {
    fetchPortfolio().catch(() => {
      showToast('获取组合信息失败', 'error');
    });
  }, [fetchPortfolio, showToast]);

  useEffect(() => {
    if (error) {
      showToast(error.message, 'error');
    }
  }, [error, showToast]);

  const totalAsset = account?.total_asset ?? 0;
  const cash = account?.cash ?? 0;
  const marketValue = account?.market_value ?? 0;
  const initialAsset = account?.initial_asset ?? totalAsset; // 使用账户的初始资产，如果没有则使用当前资产
  const totalReturn = initialAsset > 0 ? ((totalAsset - initialAsset) / initialAsset) * 100 : 0;
  
  // 计算日盈亏：当前总资产 - 昨日净值
  const yesterdayNav = account?.yesterday_nav;
  const dailyPnLValue = yesterdayNav !== undefined && yesterdayNav !== null 
    ? totalAsset - yesterdayNav 
    : dailyPnL; // 如果没有昨日净值，使用持仓盈亏作为fallback
  
  // 格式化货币显示
  const totalAssetFormatted = formatCurrency(totalAsset);
  const cashFormatted = formatCurrency(cash);
  const marketValueFormatted = formatCurrency(marketValue);
  const dailyPnLFormatted = formatCurrency(Math.abs(dailyPnLValue));

  return (
    <div className="p-4 md:p-8 h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-6 md:space-y-8">
        
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">💼 模拟盘 (Portfolio)</h2>
            <p className="text-gray-500 text-sm mt-1">实时持仓跟踪 (Real-time Position Tracking)</p>
          </div>
        </div>

        {/* Top Asset Cards */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            {[1, 2, 3, 4].map((i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <TrendingUp size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">总资产 (Total Asset)</p>
               <h3 className={`text-3xl font-bold flex items-baseline gap-1 ${totalReturn > 0 ? 'text-ashare-red' : totalReturn < 0 ? 'text-ashare-green' : 'text-gray-900'}`}>
                 <span>¥{totalAssetFormatted.integer}</span>
                 {totalAssetFormatted.decimal && (
                   <span className="text-xl">{totalAssetFormatted.decimal}</span>
                 )}
               </h3>
               {totalReturn !== 0 && (
                 <p className={`text-sm mt-1 ${totalReturn > 0 ? 'text-ashare-red' : 'text-ashare-green'}`}>
                   {totalReturn > 0 ? '+' : ''}{totalReturn.toFixed(2)}%
                 </p>
               )}
            </div>
            
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <BarChart3 size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">持仓市值 (Market Value)</p>
               <h3 className="text-3xl font-bold flex items-baseline gap-1 text-gray-900">
                 <span>¥{marketValueFormatted.integer}</span>
                 {marketValueFormatted.decimal && (
                   <span className="text-xl">{marketValueFormatted.decimal}</span>
                 )}
               </h3>
            </div>
            
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <Activity size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">可用现金 (Available Cash)</p>
               <h3 className="text-3xl font-bold flex items-baseline gap-1 text-gray-900">
                 <span>¥{cashFormatted.integer}</span>
                 {cashFormatted.decimal && (
                   <span className="text-xl">{cashFormatted.decimal}</span>
                 )}
               </h3>
            </div>

            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm relative overflow-hidden">
               <div className="absolute top-0 right-0 p-4 opacity-5">
                 <TrendingDown size={100} />
               </div>
               <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">日盈亏 (Day P&L)</p>
               <h3 className={`text-3xl font-bold flex items-baseline gap-1 ${dailyPnLValue > 0 ? 'text-ashare-red' : dailyPnLValue < 0 ? 'text-ashare-green' : 'text-gray-900'}`}>
                 <span>{dailyPnLValue > 0 ? '+' : dailyPnLValue < 0 ? '-' : ''}¥{dailyPnLFormatted.integer}</span>
                 {dailyPnLFormatted.decimal && (
                   <span className="text-xl">{dailyPnLFormatted.decimal}</span>
                 )}
               </h3>
               {yesterdayNav !== undefined && yesterdayNav !== null && yesterdayNav > 0 && (
                 <p className={`text-sm mt-1 ${dailyPnLValue > 0 ? 'text-ashare-red' : dailyPnLValue < 0 ? 'text-ashare-green' : 'text-gray-500'}`}>
                   {dailyPnLValue > 0 ? '+' : ''}{((dailyPnLValue / yesterdayNav) * 100).toFixed(2)}%
                 </p>
               )}
            </div>
          </div>
        )}

        {/* Holdings Table */}
        {loading ? (
          <SkeletonCard className="min-h-[400px]" />
        ) : (
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left min-w-[800px]">
                <thead className="bg-gray-50/50">
                  <tr>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider">资产 (Asset)</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">持仓 (Position)</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">成本/价格 (Cost/Price)</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">盈亏 (P&L)</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-right">市值 (Market Value)</th>
                    <th className="py-4 px-6 text-xs font-semibold text-gray-500 uppercase tracking-wider text-center">操作 (Actions)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {positions.map((pos) => {
                    const cost = pos.cost ?? pos.avg_price ?? 0;
                    const currentPrice = pos.current_price ?? 0;
                    const totalVol = pos.total_vol ?? pos.shares ?? 0;
                    const availVol = pos.avail_vol ?? totalVol;
                    
                    const pl = cost > 0 && currentPrice > 0 ? (currentPrice - cost) / cost * 100 : 0;
                    const plValue = (currentPrice - cost) * totalVol;
                    const marketValue = currentPrice * totalVol;

                    const plColor = pl > 0 ? 'text-ashare-red' : pl < 0 ? 'text-ashare-green' : 'text-gray-500';
                    const plSign = pl > 0 ? '+' : '';

                    return (
                      <tr 
                        key={pos.id} 
                        className="transition-colors hover:bg-gray-50"
                      >
                        <td className="py-4 px-6">
                          <div className="font-bold text-gray-900">{pos.name}</div>
                          <div className="text-xs text-gray-400 font-mono">{pos.code}</div>
                        </td>
                        <td className="py-4 px-6 text-right font-mono text-gray-600">
                          {totalVol} / {availVol}
                        </td>
                        <td className="py-4 px-6 text-right">
                          <div className="font-mono text-gray-600">{cost.toFixed(2)}</div>
                          <div className="font-mono text-gray-900 font-medium text-sm">
                            {currentPrice > 0 ? currentPrice.toFixed(2) : 'N/A'}
                          </div>
                        </td>
                        <td className={`py-4 px-6 text-right ${plColor}`}>
                          <div className="font-mono font-bold">
                            {plSign}{pl.toFixed(2)}%
                          </div>
                          <div className="font-mono text-sm">
                            {plSign}¥{Math.abs(plValue).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right font-mono text-gray-900">
                          ¥{marketValue.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="py-4 px-6 text-center">
                          <button
                            type="button"
                            onClick={() => setSellModalPosition(pos)}
                            disabled={availVol === 0}
                            className={`
                              inline-flex items-center gap-1 px-3 py-1.5 rounded-md text-sm font-medium
                              transition-colors
                              ${availVol === 0
                                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                : 'bg-red-50 text-red-600 hover:bg-red-100 active:bg-red-200'
                              }
                            `}
                            title={availVol === 0 ? '无可用数量 (No Available Volume)' : '卖出 (Sell)'}
                          >
                            {availVol === 0 ? '不可卖' : '卖出 (Sell)'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {positions.length === 0 && (
                <div className="p-8 text-center text-gray-400">
                  当前无持仓 (No Positions)
                </div>
              )}
            </div>
          </div>
        )}

        {/* Transaction Log */}
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          <button
            type="button"
            onClick={() => setIsHistoryOpen(!isHistoryOpen)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">📜</span>
              <span className="font-semibold text-gray-900">交易记录 (History)</span>
            </div>
            {isHistoryOpen ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
          
          {isHistoryOpen && (
            <div className="border-t border-gray-100 max-h-96 overflow-y-auto">
              {orders.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  暂无交易记录 (No Transaction History)
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {orders.map((order) => {
                    const actionText = order.action === 'BUY' ? '买入' : '卖出';
                    const actionColor = order.action === 'BUY' ? 'text-ashare-red' : 'text-ashare-green';
                    const date = order.created_at 
                      ? new Date(order.created_at).toLocaleString('zh-CN', { 
                          year: 'numeric', 
                          month: '2-digit', 
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit'
                        })
                      : order.trade_date;
                    
                    return (
                      <div key={order.order_id} className="p-4 hover:bg-gray-50 transition-colors">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={`font-semibold ${actionColor}`}>
                              {actionText}
                            </span>
                            <span className="font-mono text-gray-900">{order.ts_code}</span>
                            <span className="text-gray-600">{order.volume} 股</span>
                            <span className="text-gray-600">@</span>
                            <span className="font-mono text-gray-900">¥{order.price.toFixed(2)}</span>
                          </div>
                          <span className="text-xs text-gray-400">{date}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sell Order Modal */}
        {sellModalPosition && (
          <SellOrderModal
            position={sellModalPosition}
            isOpen={!!sellModalPosition}
            onClose={() => {
              setSellModalPosition(null);
              fetchPortfolio(); // 刷新数据
            }}
          />
        )}
      </div>
    </div>
  );
};

export default Portfolio;
