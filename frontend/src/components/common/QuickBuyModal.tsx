/**
 * Quick Buy Modal Component
 */
import { useState, useEffect } from 'react';
import type React from 'react';
import { X } from 'lucide-react';
import { usePortfolioStore } from '../../store/portfolioStore';
import { useToast } from './Toast';

interface QuickBuyModalProps {
  stock: {
    code: string;
    name: string;
    price: number;
  };
  isOpen: boolean;
  onClose: () => void;
}

const QuickBuyModal: React.FC<QuickBuyModalProps> = ({ stock, isOpen, onClose }) => {
  const { placeOrder, account } = usePortfolioStore();
  const { showToast } = useToast();
  const [volume, setVolume] = useState<string>('100');
  const [price, setPrice] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      // 重置表单，默认价格为股票当前价格
      setVolume('100');
      setPrice(stock.price > 0 ? stock.price.toFixed(2) : '');
    }
  }, [isOpen, stock.price]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const volNum = parseInt(volume, 10);
    const priceNum = parseFloat(price);

    // 验证
    if (!volNum || volNum <= 0) {
      showToast('请输入有效的数量', 'error');
      return;
    }

    if (!priceNum || priceNum <= 0) {
      showToast('请输入有效的价格', 'error');
      return;
    }

    // 检查资金是否充足（包含手续费 0.2%）
    const feeRate = 0.002;
    const fee = priceNum * volNum * feeRate;
    const requiredCash = priceNum * volNum + fee;
    const availableCash = account?.cash ?? 0;

    if (requiredCash > availableCash) {
      showToast(`资金不足，需要 ${requiredCash.toFixed(2)}，可用 ${availableCash.toFixed(2)}`, 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      await placeOrder({
        action: 'BUY',
        ts_code: stock.code,
        price: priceNum,
        volume: volNum,
      });
      
      showToast(`已买入 ${stock.name} ${volNum} 股 @ ${priceNum.toFixed(2)}`, 'success');
      onClose();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '买入失败';
      showToast(errorMessage, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const availableCash = account?.cash ?? 0;
  const priceNum = parseFloat(price) || 0;
  const volNum = parseInt(volume, 10) || 0;
  const feeRate = 0.002;
  const estimatedCost = priceNum * volNum * (1 + feeRate);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-bold text-gray-900">快速买入 {stock.name}</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={isSubmitting}
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              可用现金 (Available Cash)
            </label>
            <div className="text-lg font-mono text-gray-900 bg-gray-50 p-3 rounded-lg">
              ¥{availableCash.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
          </div>

          <div>
            <label htmlFor="volume" className="block text-sm font-medium text-gray-700 mb-2">
              买入数量 (Volume) *
            </label>
            <input
              id="volume"
              type="number"
              min="1"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入买入数量"
              required
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-2">
              买入价格 (Price) *
            </label>
            <input
              id="price"
              type="number"
              step="0.01"
              min="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入买入价格"
              required
              disabled={isSubmitting}
            />
            <p className="mt-1 text-xs text-gray-500">
              当前价格: {stock.price.toFixed(2)}
            </p>
          </div>

          {priceNum > 0 && volNum > 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="text-sm text-gray-700">
                <div className="flex justify-between mb-1">
                  <span>预计成本:</span>
                  <span className="font-mono">¥{(priceNum * volNum).toFixed(2)}</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span>手续费 (0.2%):</span>
                  <span className="font-mono">¥{(priceNum * volNum * feeRate).toFixed(2)}</span>
                </div>
                <div className="flex justify-between font-bold text-gray-900 pt-1 border-t border-blue-200">
                  <span>总计:</span>
                  <span className="font-mono">¥{estimatedCost.toFixed(2)}</span>
                </div>
                {estimatedCost > availableCash && (
                  <p className="text-red-600 text-xs mt-2">⚠️ 资金不足</p>
                )}
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={isSubmitting}
            >
              取消 (Cancel)
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting || estimatedCost > availableCash}
            >
              {isSubmitting ? '提交中...' : '确认买入 (Confirm Buy)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default QuickBuyModal;
