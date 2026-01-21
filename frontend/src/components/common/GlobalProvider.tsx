/**
 * Global Provider - 全局 Provider
 * 初始化全局 Store 和主题系统
 */
import React, { useEffect } from 'react';
import { useGlobalStore } from '../../store/globalStore';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

interface GlobalProviderProps {
  children: React.ReactNode;
}

// Toast 组件（简化版，用于全局通知）
const Toast: React.FC<{
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  onClose: () => void;
  duration?: number;
}> = ({ type, message, onClose }) => {
  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle size={20} className="text-green-600" />;
      case 'error':
        return <AlertCircle size={20} className="text-red-600" />;
      case 'warning':
        return <AlertTriangle size={20} className="text-yellow-600" />;
      default:
        return <Info size={20} className="text-blue-600" />;
    }
  };

  const getBgColor = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      case 'warning':
        return 'bg-yellow-50 border-yellow-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div
      className={`flex items-center gap-3 p-4 rounded-lg border shadow-lg min-w-[300px] ${getBgColor()} animate-in slide-in-from-right`}
    >
      {getIcon()}
      <p className="flex-1 text-sm text-gray-900">{message}</p>
      <button
        onClick={onClose}
        className="text-gray-400 hover:text-gray-600"
      >
        <X size={16} />
      </button>
    </div>
  );
};

export const GlobalProvider: React.FC<GlobalProviderProps> = ({ children }) => {
  const { theme, notifications, removeNotification } = useGlobalStore();

  // 初始化主题
  useEffect(() => {
    // 应用主题到 document
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  // 从 localStorage 恢复主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
    if (savedTheme && savedTheme !== theme) {
      useGlobalStore.getState().setTheme(savedTheme);
    }
  }, []);

  return (
    <>
      {children}
      {/* 全局通知 Toast */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {notifications.map((notification) => (
          <Toast
            key={notification.id}
            id={notification.id}
            type={notification.type}
            message={notification.message}
            onClose={() => removeNotification(notification.id)}
            duration={notification.duration}
          />
        ))}
      </div>
    </>
  );
};
