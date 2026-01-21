/**
 * useTheme Hook - 主题切换 Hook
 */
import { useGlobalStore } from '../store/globalStore';
import type { Theme } from '../store/globalStore';

export function useTheme() {
  const theme = useGlobalStore((state) => state.theme);
  const setTheme = useGlobalStore((state) => state.setTheme);

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  return {
    theme,
    setTheme,
    toggleTheme,
    isDark: theme === 'dark',
    isLight: theme === 'light',
  };
}
