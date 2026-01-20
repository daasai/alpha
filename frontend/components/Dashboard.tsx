import React from 'react';
import { ResponsiveContainer, ComposedChart, Line, XAxis, YAxis, Tooltip, Area, CartesianGrid } from 'recharts';
import { MOCK_MARKET_DATA } from '../constants';
import { ArrowUp, ArrowDown } from 'lucide-react';

const Dashboard: React.FC = () => {
  // Calculate simple stats based on mock data
  const latestData = MOCK_MARKET_DATA[MOCK_MARKET_DATA.length - 1];
  const isBull = latestData.price > latestData.bbi;
  const regimeColor = isBull ? 'text-ashare-red' : 'text-ashare-green';
  const regimeLabel = isBull ? '🟢 多头 (进攻)' : '🔴 空头 (防守)';

  return (
    <div className="p-8 h-full overflow-y-auto bg-gray-50">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold text-gray-900">驾驶舱 (Dashboard)</h2>
          <p className="text-gray-500 text-sm mt-1">Today's Morning Briefing</p>
        </div>

        {/* Top Row: KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Market Regime */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Market Regime</span>
            <div className={`text-xl font-bold ${regimeColor} flex items-center gap-2`}>
              {regimeLabel}
            </div>
            <div className="text-xs text-gray-400">Trend is your friend</div>
          </div>

          {/* Sentiment */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
             <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sentiment (赚钱效应)</span>
             <div>
               <div className="flex justify-between items-end mb-1">
                 <span className="text-2xl font-bold text-gray-900">45%</span>
                 <span className="text-xs text-ashare-red">+5%</span>
               </div>
               <div className="w-full bg-gray-200 rounded-full h-2">
                 <div className="bg-ashare-red h-2 rounded-full" style={{ width: '45%' }}></div>
               </div>
             </div>
          </div>

          {/* Target Position */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Target Position</span>
            <div className="flex items-center gap-3">
              <span className="text-3xl font-bold text-gray-900">100%</span>
              <span className="bg-ashare-red/10 text-ashare-red px-2 py-0.5 rounded text-xs font-medium">Full On</span>
            </div>
            <div className="text-xs text-gray-400">Based on signal strength</div>
          </div>

          {/* Portfolio NAV */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col justify-between h-32">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Portfolio NAV</span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900">¥1,245,300</span>
            </div>
             <div className="flex items-center text-xs text-ashare-red">
               <ArrowUp size={12} className="mr-1" />
               <span>1.2% Today</span>
             </div>
          </div>
        </div>

        {/* Main Chart: BBI Trend */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 min-h-[500px]">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-800">上证指数 (000001.SH) vs BBI Trend</h3>
            <div className="flex gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-gray-800 rounded-full"></div>
                <span className="text-gray-600">Price</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <span className="text-gray-600">BBI</span>
              </div>
            </div>
          </div>
          
          <div className="h-[400px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={MOCK_MARKET_DATA} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
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
                {/* 
                  Note: Recharts doesn't natively support "Fill between two dynamic lines" easily.
                  We visualize this by showing both lines clearly.
                  The visual cue of Red/Green is best handled by the Market Regime card 
                  or a background strip, but for "Fintech Clean", distinct lines are best.
                */}
                <Line 
                  type="monotone" 
                  dataKey="price" 
                  stroke="#1f2937" 
                  strokeWidth={2} 
                  dot={false}
                  activeDot={{ r: 6 }}
                  name="Close Price"
                />
                <Line 
                  type="monotone" 
                  dataKey="bbi" 
                  stroke="#3b82f6" 
                  strokeWidth={2} 
                  dot={false} 
                  strokeDasharray="5 5"
                  name="BBI Indicator"
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;