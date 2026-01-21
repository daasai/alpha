/**
 * Global Store - 全局状态管理
 * 管理用户信息、主题设置、全局通知等
 */
import { create } from 'zustand';

export type Theme = 'light' | 'dark';

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: number;
  duration?: number;  // 自动消失时间（毫秒），0表示不自动消失
}

export interface User {
  id?: string;
  name?: string;
  email?: string;
}

interface GlobalState {
  // 用户信息
  user: User | null;
  isAuthenticated: boolean;
  
  // 主题设置
  theme: Theme;
  
  // 全局通知
  notifications: Notification[];
  
  // 全局加载状态
  globalLoading: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setAuthenticated: (isAuthenticated: boolean) => void;
  setTheme: (theme: Theme) => void;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  setGlobalLoading: (loading: boolean) => void;
}

export const useGlobalStore = create<GlobalState>((set) => ({
  // 初始状态
  user: null,
  isAuthenticated: false,
  theme: (localStorage.getItem('theme') as Theme) || 'light',
  notifications: [],
  globalLoading: false,
  
  // Actions
  setUser: (user) => set({ user }),
  setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
  
  setTheme: (theme) => {
    localStorage.setItem('theme', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    set({ theme });
  },
  
  addNotification: (notification) => {
    const id = `notification-${Date.now()}-${Math.random()}`;
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: Date.now(),
      duration: notification.duration ?? 5000,  // 默认5秒
    };
    
    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));
    
    // 自动移除通知
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      }, newNotification.duration);
    }
  },
  
  removeNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),
  
  clearNotifications: () => set({ notifications: [] }),
  
  setGlobalLoading: (loading) => set({ globalLoading: loading }),
}));
