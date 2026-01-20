import React, { useState } from 'react';
import { MOCK_HUNTER_RESULTS } from '../constants';
import { Search, SlidersHorizontal, Plus } from 'lucide-react';

const Hunter: React.FC = () => {
  const [rpsThreshold, setRpsThreshold] = useState(80);
  const [volumeRatio, setVolumeRatio] = useState(1.5);
  const [isFiltersOpen, setIsFiltersOpen] = useState(true);

  // Filter logic (simulated)
  const filteredResults = MOCK_HUNTER_RESULTS.filter(item => 
    item.rps >= rpsThreshold - 20 // Loose filtering for mock data variety
  );

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header & Controls */}
      <div className="border-b border-gray-100 bg-white p-6 sticky top-0 z-10">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">🔭 猎场 (Hunter)</h2>
          <button 
            onClick={() => setIsFiltersOpen(!isFiltersOpen)}
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors"
          >
            <SlidersHorizontal size={16} />
            {isFiltersOpen ? '收起筛选' : '展开筛选'}
          </button>
        </div>

        {/* Collapsible Search Bar */}
        <div className={`transition-all duration-300 overflow-hidden ${isFiltersOpen ? 'max-h-96 md:max-h-48 opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8 bg-gray-50 p-6 rounded-xl">
             {/* Search Input */}
             <div className="relative">
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Search Ticker</label>
                <div className="relative">
                  <input 
                    type="text" 
                    placeholder="e.g. 600519" 
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black transition-all"
                  />
                  <Search size={18} className="absolute left-3 top-2.5 text-gray-400" />
                </div>
             </div>

             {/* RPS Slider */}
             <div>
               <div className="flex justify-between mb-2">
                 <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Min RPS Score</label>
                 <span className="text-xs font-bold text-ashare-red">{rpsThreshold}</span>
               </div>
               <input 
                 type="range" 
                 min="50" 
                 max="100" 
                 value={rpsThreshold} 
                 onChange={(e) => setRpsThreshold(parseInt(e.target.value))}
                 className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black"
               />
             </div>

             {/* Volume Ratio Slider */}
             <div>
               <div className="flex justify-between mb-2">
                 <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Min Volume Ratio</label>
                 <span className="text-xs font-bold text-blue-600">{volumeRatio}x</span>
               </div>
               <input 
                 type="range" 
                 min="0" 
                 max="10" 
                 step="0.1"
                 value={volumeRatio} 
                 onChange={(e) => setVolumeRatio(parseFloat(e.target.value))}
                 className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-black"
               />
             </div>
          </div>
        </div>
      </div>

      {/* Results Table - Infinite Canvas Style */}
      <div className="flex-1 overflow-auto p-4 md:p-6 bg-white">
        <div className="w-full overflow-x-auto pb-6">
          <table className="w-full text-left border-collapse min-w-[800px]">
            <thead>
              <tr className="border-b border-gray-100">
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-32">Code/Name</th>
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-24 text-right">Price</th>
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-24 text-right">Chg%</th>
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-48">RPS Strength</th>
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">AI Analysis</th>
                <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-16 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredResults.map((stock) => {
                const isUp = stock.changePercent > 0;
                const changeColor = isUp ? 'text-ashare-red' : 'text-ashare-green';
                
                return (
                  <tr key={stock.id} className="hover:bg-gray-50 transition-colors group">
                    <td className="py-4 px-4">
                      <div className="font-bold text-gray-900">{stock.name}</div>
                      <div className="text-xs text-gray-400 font-mono">{stock.code}</div>
                    </td>
                    <td className="py-4 px-4 text-right font-medium text-gray-900">
                      {stock.price.toFixed(2)}
                    </td>
                    <td className={`py-4 px-4 text-right font-medium ${changeColor}`}>
                      {isUp ? '+' : ''}{stock.changePercent.toFixed(2)}%
                    </td>
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                         <span className="text-xs font-bold text-gray-600 w-6">{stock.rps}</span>
                         <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                           <div 
                              className="h-full bg-ashare-red" 
                              style={{ width: `${stock.rps}%` }}
                           ></div>
                         </div>
                      </div>
                    </td>
                    <td className="py-4 px-4 max-w-md">
                      <div className="text-sm text-gray-600 truncate max-w-[200px] md:max-w-md cursor-pointer hover:text-gray-900" title={stock.aiAnalysis}>
                        <span className="mr-2">✨</span>
                        {stock.aiAnalysis}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <button className="p-2 rounded-full hover:bg-gray-200 text-gray-400 hover:text-black transition-colors">
                        <Plus size={18} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          
          {filteredResults.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-gray-400">
              <Search size={48} className="mb-4 opacity-20" />
              <p>No high-signal stocks found based on current filters.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Hunter;