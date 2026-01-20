import { useState, useEffect, type FC } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Plus, Search, SlidersHorizontal } from 'lucide-react';
import { useHunterFilters, useHunterScan } from '../../hooks/useHunter';
import { useHunterStore } from '../../store/hunterStore';
import { SkeletonTable } from '../common/Loading';
import { useToast } from '../common/Toast';
import * as portfolioApi from '../../api/services/portfolio';

const Hunter: FC = () => {
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const { 
    results, 
    rpsThreshold, 
    volumeRatio, 
    setRpsThreshold, 
    setVolumeRatio
  } = useHunterStore();
  
  const [isFiltersOpen, setIsFiltersOpen] = useState(true);
  const [addingToPortfolio, setAddingToPortfolio] = useState<string | null>(null);
  const { scan, loading: scanLoading, error: scanError } = useHunterScan();
  const { loading: filtersLoading } = useHunterFilters();

  // Filters are automatically set by the hook

  useEffect(() => {
    if (scanError) {
      const errorMessage = scanError.message || '扫描失败';
      showToast(errorMessage, 'error');
    }
  }, [scanError, showToast]);

  // Auto scan when autoScan parameter is present
  useEffect(() => {
    const autoScan = searchParams.get('autoScan') === 'true';
    if (autoScan) {
      scan({
        rps_threshold: rpsThreshold,
        volume_ratio_threshold: volumeRatio,
      });
      // Remove the parameter to avoid repeated triggers
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        newParams.delete('autoScan');
        return newParams;
      });
    }
  }, [searchParams, scan, rpsThreshold, volumeRatio, setSearchParams]);

  const handleScan = () => {
    scan({
      rps_threshold: rpsThreshold,
      volume_ratio_threshold: volumeRatio,
    });
  };

  const handleAddToPortfolio = async (stock: typeof filteredResults[0]) => {
    if (addingToPortfolio) return; // Prevent duplicate clicks
    
    setAddingToPortfolio(stock.id);
    try {
      const response = await portfolioApi.addPosition({
        code: stock.code,
        name: stock.name,
        cost: stock.price,
        shares: 100, // Default value, consistent with config
        stop_loss_price: stock.price * 0.9, // Default value, consistent with config
      });

      if (response.success && response.data) {
        showToast(`已添加 ${stock.name} 到持仓组合`, 'success');
      } else {
        showToast(response.error || response.message || '添加持仓失败', 'error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '添加持仓失败';
      showToast(errorMessage, 'error');
    } finally {
      setAddingToPortfolio(null);
    }
  };

  // Results are managed by the store, updated by the hook

  // Filter results (client-side filtering for now)
  // 注意：这里使用宽松的过滤条件，因为后端已经根据rps_threshold筛选过了
  const filteredResults = results.filter(item => 
    item.rps >= rpsThreshold - 20 // Loose filtering to show more results
  );

  const isLoading = scanLoading || filtersLoading;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header & Controls */}
      <div className="border-b border-gray-100 bg-white p-6 sticky top-0 z-10">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-900">🔭 猎场 (Hunter)</h2>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={handleScan}
              disabled={isLoading}
              className="bg-gray-900 hover:bg-black text-white font-semibold rounded-lg px-6 py-2.5 transition-all disabled:opacity-50"
            >
              {isLoading ? '扫描中...' : '执行扫描'}
            </button>
            <button 
              type="button"
              onClick={() => setIsFiltersOpen(!isFiltersOpen)}
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 transition-colors"
            >
              <SlidersHorizontal size={16} />
              {isFiltersOpen ? '收起筛选' : '展开筛选'}
            </button>
          </div>
        </div>

        {/* Collapsible Filters */}
        <div className={`transition-all duration-300 overflow-hidden ${isFiltersOpen ? 'max-h-96 md:max-h-48 opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 bg-gray-50 p-6 rounded-xl">
             {/* RPS Slider */}
             <div>
               <div className="flex justify-between mb-2">
                 <label htmlFor="rps-threshold" className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Min RPS Score</label>
                 <span className="text-xs font-bold text-ashare-red">{rpsThreshold}</span>
               </div>
               <input 
                 id="rps-threshold"
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
                 <label htmlFor="volume-ratio" className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Min Volume Ratio</label>
                 <span className="text-xs font-bold text-blue-600">{volumeRatio}x</span>
               </div>
               <input 
                 id="volume-ratio"
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

      {/* Results Table */}
      {isLoading ? (
        <div className="flex-1 overflow-auto p-4 md:p-6 bg-white">
          <SkeletonTable />
        </div>
      ) : (
        <div className="flex-1 overflow-auto p-4 md:p-6 bg-white">
          <div className="w-full overflow-x-auto pb-6">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-32">代码/名称</th>
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-24 text-right">价格</th>
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-24 text-right">涨跌幅</th>
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-48">RPS强度</th>
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">AI分析</th>
                  <th className="py-4 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider w-16 text-center">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filteredResults.map((stock) => {
                  const isUp = stock.change_percent > 0;
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
                        {isUp ? '+' : ''}{stock.change_percent.toFixed(2)}%
                      </td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-3">
                           <span className="text-xs font-bold text-gray-600 w-12">{Math.round(stock.rps)}</span>
                           <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                             <div 
                                className="h-full bg-ashare-red" 
                                style={{ width: `${Math.min(100, Math.max(0, stock.rps))}%` }}
                             ></div>
                           </div>
                        </div>
                      </td>
                      <td className="py-4 px-4 max-w-md">
                        <div className="text-sm text-gray-600 truncate max-w-[200px] md:max-w-md cursor-pointer hover:text-gray-900" title={stock.ai_analysis}>
                          <span className="mr-2">✨</span>
                          {stock.ai_analysis || '暂无分析'}
                        </div>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <button 
                          type="button" 
                          onClick={() => handleAddToPortfolio(stock)}
                          disabled={addingToPortfolio === stock.id}
                          className="p-2 rounded-full hover:bg-gray-200 text-gray-400 hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="添加到持仓组合"
                        >
                          <Plus size={18} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            
            {filteredResults.length === 0 && !isLoading && (
              <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                <Search size={48} className="mb-4 opacity-20" />
                <p className="text-center">
                  {results.length === 0 
                    ? '暂无符合条件的股票，请尝试调整筛选条件' 
                    : `已找到 ${results.length} 只股票，但当前筛选条件过滤后无结果，请尝试降低RPS阈值`}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Hunter;
