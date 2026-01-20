/**
 * Generic API Hook
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export interface UseApiOptions {
  immediate?: boolean; // Whether to fetch immediately
  onSuccess?: (data: any) => void;
  onError?: (error: Error) => void;
}

/**
 * Generic hook for API calls
 */
export function useApi<T>(
  apiCall: () => Promise<T>,
  options: UseApiOptions = {}
): UseApiState<T> & { refetch: () => Promise<void> } {
  const { immediate = true, onSuccess, onError } = options;
  
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: immediate,
    error: null,
  });

  // Use refs to store callbacks to avoid dependency issues
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  const apiCallRef = useRef(apiCall);

  // Update refs when they change
  useEffect(() => {
    onSuccessRef.current = onSuccess;
    onErrorRef.current = onError;
    apiCallRef.current = apiCall;
  }, [onSuccess, onError, apiCall]);

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      const response = await apiCallRef.current();
      setState({ data: response, loading: false, error: null });
      onSuccessRef.current?.(response);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setState({ data: null, loading: false, error });
      onErrorRef.current?.(error);
    }
  }, []); // Empty deps - using refs instead

  useEffect(() => {
    if (immediate) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [immediate]); // Only depend on immediate flag

  return {
    ...state,
    refetch: fetchData,
  };
}
