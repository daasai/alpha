/**
 * Event Bus - 事件总线
 * 支持跨 Store 通信和数据同步
 */

export type EventType =
  | 'PORTFOLIO_UPDATED'
  | 'PORTFOLIO_POSITION_ADDED'
  | 'PORTFOLIO_POSITION_UPDATED'
  | 'PORTFOLIO_POSITION_DELETED'
  | 'DASHBOARD_REFRESH'
  | 'MARKET_DATA_UPDATED'
  | 'HUNTER_SCAN_COMPLETED'
  | 'LAB_BACKTEST_COMPLETED';

export interface Event {
  type: EventType;
  payload?: any;
  timestamp: number;
}

type EventHandler = (event: Event) => void;

class EventBus {
  private handlers: Map<EventType, Set<EventHandler>> = new Map();

  /**
   * 订阅事件
   * @param type 事件类型
   * @param handler 事件处理函数
   * @returns 取消订阅函数
   */
  subscribe(type: EventType, handler: EventHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    
    this.handlers.get(type)!.add(handler);
    
    // 返回取消订阅函数
    return () => {
      const handlers = this.handlers.get(type);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.handlers.delete(type);
        }
      }
    };
  }

  /**
   * 发布事件
   * @param type 事件类型
   * @param payload 事件负载
   */
  publish(type: EventType, payload?: any): void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      const event: Event = {
        type,
        payload,
        timestamp: Date.now(),
      };
      
      handlers.forEach((handler) => {
        try {
          handler(event);
        } catch (error) {
          console.error(`Error in event handler for ${type}:`, error);
        }
      });
    }
  }

  /**
   * 取消订阅
   * @param type 事件类型
   * @param handler 事件处理函数
   */
  unsubscribe(type: EventType, handler: EventHandler): void {
    const handlers = this.handlers.get(type);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.handlers.delete(type);
      }
    }
  }

  /**
   * 清除所有订阅
   */
  clear(): void {
    this.handlers.clear();
  }
}

// 导出单例
export const eventBus = new EventBus();
