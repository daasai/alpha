import React, { useEffect } from 'react';
import { ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { ArrowUp, ArrowDown } from 'lucide-react';
import { useDashboardOverview, useMarketTrend } from '../../hooks/useDashboard';
import { useDashboardStore } from '../../store/dashboardStore';
import { SkeletonCard, SkeletonChart } from '../common/Loading';
import { useToast } from '../common/Toast';

const Dashboard: React.FC = () => {
  const { showToast } = useToast();
  const { overview, marketTrend } = useDashboardStore();
  
  // 数据来源：通过 useDashboardOverview 和 useMarketTrend hooks
  // 这些hooks调用后端API: /api/dashboard/overview 和 /api/dashboard/market-trend
  // 数据从后端 DashboardService 获取，包括：
  // - 市场状态：从Tushare API获取指数数据计算BBI
  // - 组合净值：从数据库 portfolio_positions 表计算
  // - 市场趋势：从Tushare API获取指数日线数据
  const { loading: overviewLoading, error: overviewError } = useDashboardOverview();
  const { loading: trendLoading, error: trendError } = useMarketTrend(60);

  useEffect(() => {
    if (overviewError) {
      showToast('获取市场概览失败 (Failed to fetch market overview)', 'error');
    }
  }, [overviewError, showToast]);

  useEffect(() => {
    if (trendError) {
      showToast('获取市场趋势失败 (Failed to fetch market trend)', 'error');
    }
  }, [trendError, showToast]);

  // 开发环境下验证数据来源
  useEffect(() => {
    if (import.meta.env.DEV && overview) {
      console.log('[Dashboard] 数据来源验证:', {
        source: '后端API /api/dashboard/overview',
        data: overview,
        timestamp: new Date().toISOString()
      });
    }
  }, [overview]);

  useEffect(() => {
    if (import.meta.env.DEV && marketTrend) {
      console.log('[Dashboard] 市场趋势数据来源验证:', {
        source: '后端API /api/dashboard/market-trend',
        dataPoints: marketTrend.data?.length || 0,
        indexCode: marketTrend.index_code,
        timestamp: new Date().toISOString()
      });
    }
  }, [marketTrend]);

  // Calculate stats from overview data
  const isBull = overview?.market_regime?.is_bull ?? false;
  const regimeColor = isBull ? 'text-ashare-red' : 'text-ashare-green';
  const regimeLabel = isBull ? '🟢 多头 (Bull)' : '🔴 空头 (Bear)';

  // Prepare chart data
  const chartData = marketTrend?.data?.map(item => ({
    date: item.date,
    price: item.price,
    bbi: item.bbi,
  })) || [];

  const isLoading = overviewLoading || trendLoading;

  return (
    <div className="p-8 h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">驾驶舱 (Dashboard)</h2>
          <p className="text-gray-500 text-sm mt-1">今日早报 (Daily Briefing)</p>
        </div>

        {/* Top Row: KPI Cards */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <SkeletonCard key={i} className="h-32" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {/* Market Regime */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">市场状态 (Market Regime)</span>
              <div className={`text-xl font-bold ${regimeColor} flex items-center gap-2`}>
                {regimeLabel}
              </div>
              <div className="text-xs text-gray-400">趋势是你的朋友 (Trend is Your Friend)</div>
            </div>

            {/* Sentiment */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
               <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sentiment (赚钱效应)</span>
               <div>
                 <div className="flex justify-between items-end mb-1">
                   <span className="text-2xl font-bold text-gray-900">
                     {overview?.sentiment?.sentiment?.toFixed(1) || '0'}%
                   </span>
                   {overview?.sentiment?.change && (
                     <span className="text-xs text-ashare-red">
                       {overview.sentiment.change > 0 ? '+' : ''}{overview.sentiment.change.toFixed(1)}%
                     </span>
                   )}
                 </div>
                 <div className="w-full bg-gray-200 rounded-full h-2">
                   <div 
                      className="bg-ashare-red h-2 rounded-full" 
                      style={{ width: `${overview?.sentiment?.sentiment || 0}%` }}
                   ></div>
                 </div>
               </div>
            </div>

            {/* Target Position */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">目标仓位 (Target Position)</span>
              <div className="flex items-center gap-3">
                <span className="text-3xl font-bold text-gray-900">
                  {overview?.target_position?.position || 0}%
                </span>
                <span className="bg-ashare-red/10 text-ashare-red px-2 py-0.5 rounded text-xs font-medium">
                  {overview?.target_position?.label === 'Full On' ? '满仓 (Full On)' : overview?.target_position?.label === 'Defensive' ? '防守 (Defensive)' : overview?.target_position?.label || 'N/A'}
                </span>
              </div>
              <div className="text-xs text-gray-400">基于信号强度 (Based on Signal Strength)</div>
            </div>

            {/* Portfolio NAV */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
              <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">组合净值 (Portfolio NAV)</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-gray-900">
                  ¥{overview?.portfolio_nav?.nav?.toLocaleString() || '0'}
                </span>
              </div>
               {overview?.portfolio_nav?.change_percent !== undefined && (
                 <div className={`flex items-center text-xs ${overview.portfolio_nav.change_percent >= 0 ? 'text-ashare-red' : 'text-ashare-green'}`}>
                   {overview.portfolio_nav.change_percent >= 0 ? (
                     <ArrowUp size={12} className="mr-1" />
                   ) : (
                     <ArrowDown size={12} className="mr-1" />
                   )}
                   <span>{overview.portfolio_nav.change_percent > 0 ? '+' : ''}{overview.portfolio_nav.change_percent.toFixed(1)}% 今日 (Today)</span>
                 </div>
               )}
            </div>
          </div>
        )}

        {/* Main Chart: BBI Trend */}
        {isLoading ? (
          <SkeletonChart />
        ) : (
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 min-h-[500px]">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-gray-800">
                {marketTrend?.index_name || '上证指数'} ({marketTrend?.index_code || '000001.SH'}) vs BBI趋势
              </h3>
              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-gray-800 rounded-full"></div>
                  <span className="text-gray-600">价格 (Price)</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                  <span className="text-gray-600">BBI指标 (BBI Indicator)</span>
                </div>
              </div>
            </div>
            
            {chartData.length > 0 ? (
              <div className="h-[400px] w-full min-h-[400px]">
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8884d8" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#8884d8" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis 
                      dataKey="date" 
                      tick={{ fontSize: 12, fill: '#9ca3af' }} 
                      axisLine={false} 
                      tickLine={false}
                      minTickGap={30}
                    />
                    <YAxis 
                      domain={['auto', 'auto']} 
                      tick={{ fontSize: 12, fill: '#9ca3af' }} 
                      axisLine={false} 
                      tickLine={false} 
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#fff', borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                      itemStyle={{ fontSize: '12px' }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="price" 
                      stroke="#1f2937" 
                      strokeWidth={2} 
                      dot={false}
                      activeDot={{ r: 6 }}
                      name="收盘价 (Close Price)"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="bbi" 
                      stroke="#3b82f6" 
                      strokeWidth={2} 
                      dot={false} 
                      strokeDasharray="5 5"
                      name="BBI指标 (BBI Indicator)"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-[400px] flex items-center justify-center text-gray-400">
                暂无数据 (No Data)
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
