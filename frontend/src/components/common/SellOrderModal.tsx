/**
 * Sell Order Modal Component
 */
import { useState, useEffect } from 'react';
import type React from 'react';
import { X } from 'lucide-react';
import { usePortfolioStore } from '../../store/portfolioStore';
import { useToast } from './Toast';
import type { PortfolioPosition } from '../../types/api';

interface SellOrderModalProps {
  position: PortfolioPosition;
  isOpen: boolean;
  onClose: () => void;
}

const SellOrderModal: React.FC<SellOrderModalProps> = ({ position, isOpen, onClose }) => {
  const { placeOrder } = usePortfolioStore();
  const { showToast } = useToast();
  const [volume, setVolume] = useState<string>('');
  const [price, setPrice] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const availVol = position.avail_vol ?? position.shares ?? 0;
  const currentPrice = position.current_price ?? 0;

  useEffect(() => {
    if (isOpen) {
      // 重置表单
      setVolume('');
      setPrice(currentPrice > 0 ? currentPrice.toFixed(2) : '');
    }
  }, [isOpen, currentPrice]);

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

    if (volNum > availVol) {
      showToast(`可用数量不足，当前可用：${availVol} 股`, 'error');
      return;
    }

    if (!priceNum || priceNum <= 0) {
      showToast('请输入有效的价格', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      await placeOrder({
        action: 'SELL',
        ts_code: position.code,
        price: priceNum,
        volume: volNum,
      });
      
      showToast(`已卖出 ${position.name} ${volNum} 股 @ ${priceNum.toFixed(2)}`, 'success');
      onClose();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '卖出失败';
      showToast(errorMessage, 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h3 className="text-lg font-bold text-gray-900">卖出 {position.name}</h3>
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
              可用数量 (Available)
            </label>
            <div className="text-lg font-mono text-gray-900 bg-gray-50 p-3 rounded-lg">
              {availVol} 股
            </div>
          </div>

          <div>
            <label htmlFor="volume" className="block text-sm font-medium text-gray-700 mb-2">
              卖出数量 (Volume) *
            </label>
            <input
              id="volume"
              type="number"
              min="1"
              max={availVol}
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入卖出数量"
              required
              disabled={isSubmitting}
            />
          </div>

          <div>
            <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-2">
              卖出价格 (Price) *
            </label>
            <input
              id="price"
              type="number"
              step="0.01"
              min="0.01"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="请输入卖出价格"
              required
              disabled={isSubmitting}
            />
            {currentPrice > 0 && (
              <p className="mt-1 text-xs text-gray-500">
                当前价格: {currentPrice.toFixed(2)}
              </p>
            )}
          </div>

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
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              {isSubmitting ? '提交中...' : '确认卖出 (Confirm Sell)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SellOrderModal;
