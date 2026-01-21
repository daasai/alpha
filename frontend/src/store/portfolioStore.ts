/**
 * Portfolio Store
 * Enhanced version: Integrated with Event Bus for cross-store communication
 */
import { create } from 'zustand';
import type { PortfolioPosition, PortfolioMetrics, Account, Order, OrderParams } from '../types/api';
import { eventBus } from './eventBus';
import * as portfolioApi from '../api/services/portfolio';

interface PortfolioState {
  positions: PortfolioPosition[];
  metrics: PortfolioMetrics | null;
  account: Account | null;
  orders: Order[];
  loading: boolean;
  error: Error | null;
  
  // Actions
  setPositions: (positions: PortfolioPosition[]) => void;
  addPosition: (position: PortfolioPosition) => void;
  updatePosition: (id: string, position: Partial<PortfolioPosition>) => void;
  removePosition: (id: string) => void;
  setMetrics: (metrics: PortfolioMetrics) => void;
  setAccount: (account: Account | null) => void;
  setOrders: (orders: Order[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: Error | null) => void;
  fetchPortfolio: () => Promise<void>;
  placeOrder: (orderParams: OrderParams) => Promise<Order>;
}

export const usePortfolioStore = create<PortfolioState>((set, get) => ({
  positions: [],
  metrics: null,
  account: null,
  orders: [],
  loading: false,
  error: null,
  
  setPositions: (positions) => {
    set({ positions });
    // 发布事件：持仓列表更新
    eventBus.publish('PORTFOLIO_UPDATED', { positions });
  },
  
  addPosition: (position) => {
    set((state) => ({
      positions: [...state.positions, position]
    }));
    // 发布事件：添加持仓
    eventBus.publish('PORTFOLIO_POSITION_ADDED', { position });
    eventBus.publish('PORTFOLIO_UPDATED', { positions: get().positions });
  },
  
  updatePosition: (id, updates) => {
    set((state) => ({
      positions: state.positions.map(pos =>
        pos.id === id ? { ...pos, ...updates } : pos
      )
    }));
    // 发布事件：更新持仓
    const updatedPosition = get().positions.find(p => p.id === id);
    if (updatedPosition) {
      eventBus.publish('PORTFOLIO_POSITION_UPDATED', { position: updatedPosition });
      eventBus.publish('PORTFOLIO_UPDATED', { positions: get().positions });
    }
  },
  
  removePosition: (id) => {
    set((state) => ({
      positions: state.positions.filter(pos => pos.id !== id)
    }));
    // 发布事件：删除持仓
    eventBus.publish('PORTFOLIO_POSITION_DELETED', { positionId: id });
    eventBus.publish('PORTFOLIO_UPDATED', { positions: get().positions });
  },
  
  setMetrics: (metrics) => {
    set({ metrics });
    // 发布事件：指标更新
    eventBus.publish('PORTFOLIO_UPDATED', { metrics });
  },
  
  setAccount: (account) => {
    set({ account });
    eventBus.publish('PORTFOLIO_UPDATED', { account });
  },
  
  setOrders: (orders) => {
    set({ orders });
    eventBus.publish('PORTFOLIO_UPDATED', { orders });
  },
  
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  fetchPortfolio: async () => {
    set({ loading: true, error: null });
    try {
      // 获取组合概览（账户 + 持仓）
      const overviewResponse = await portfolioApi.getPortfolioOverview();
      if (overviewResponse.success && overviewResponse.data) {
        set({
          account: overviewResponse.data.account,
          positions: overviewResponse.data.positions,
        });
      }
      
      // 获取订单历史
      const historyResponse = await portfolioApi.getOrderHistory(50);
      if (historyResponse.success && historyResponse.data) {
        set({ orders: historyResponse.data.orders });
      }
      
      set({ loading: false });
    } catch (error) {
      const err = error instanceof Error ? error : new Error('获取组合信息失败');
      set({ error: err, loading: false });
      throw err;
    }
  },
  
  placeOrder: async (orderParams: OrderParams): Promise<Order> => {
    set({ loading: true, error: null });
    try {
      const response = await portfolioApi.placeOrder(orderParams);
      if (response.success && response.data) {
        // 添加新订单到列表开头
        const newOrder = response.data;
        set((state) => ({
          orders: [newOrder, ...state.orders],
        }));
        
        // 重新获取组合状态以更新账户和持仓
        await get().fetchPortfolio();
        
        set({ loading: false });
        return response.data;
      } else {
        throw new Error(response.error || '订单执行失败');
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error('订单执行失败');
      set({ error: err, loading: false });
      throw err;
    }
  },
}));
