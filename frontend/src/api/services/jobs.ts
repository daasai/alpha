/**
 * Jobs API Service
 */
import apiClient from '../client';
import type { ApiResponse } from '../../types/api';

export interface TriggerRequest {
  trade_date?: string;  // YYYYMMDD格式
  force?: boolean;
}

export interface TriggerResponse {
  success: boolean;
  execution_id: string;
  message: string;
  trade_date: string;
}

export interface ExecutionStatus {
  execution_id: string;
  trade_date: string;
  trigger_type: string;
  status: string;
  is_duplicate: boolean;
  started_at: string;
  completed_at?: string | null;
  duration_seconds?: number | null;
  steps_completed?: string[] | null;
  errors?: string[] | null;
  retry_count: number;
  max_retries: number;
  next_retry_at?: string | null;
}

export interface ExecutionHistory {
  total: number;
  executions: ExecutionStatus[];
}

/**
 * Trigger daily runner task
 */
export const triggerDailyRunner = async (
  request: TriggerRequest = {}
): Promise<ApiResponse<TriggerResponse>> => {
  const response = await apiClient.post('/api/v1/jobs/daily-runner/trigger', request);
  return response as unknown as ApiResponse<TriggerResponse>;
};

/**
 * Get daily runner status
 */
export const getDailyRunnerStatus = async (
  trade_date?: string
): Promise<ApiResponse<ExecutionStatus>> => {
  const params = trade_date ? { trade_date } : {};
  const response = await apiClient.get('/api/v1/jobs/daily-runner/status', { params });
  return response as unknown as ApiResponse<ExecutionStatus>;
};

/**
 * Get daily runner execution history
 */
export const getDailyRunnerHistory = async (
  trade_date?: string,
  status?: string,
  limit: number = 50
): Promise<ApiResponse<ExecutionHistory>> => {
  const params: any = { limit };
  if (trade_date) params.trade_date = trade_date;
  if (status) params.status = status;
  
  const response = await apiClient.get('/api/v1/jobs/daily-runner/history', { params });
  return response as unknown as ApiResponse<ExecutionHistory>;
};

/**
 * Get execution detail by ID
 */
export const getExecutionDetail = async (
  execution_id: string
): Promise<ApiResponse<ExecutionStatus>> => {
  const response = await apiClient.get(`/api/v1/jobs/daily-runner/${execution_id}`);
  return response as unknown as ApiResponse<ExecutionStatus>;
};

/**
 * Retry failed execution
 */
export const retryExecution = async (
  execution_id: string
): Promise<ApiResponse<{ success: boolean; message: string; execution_id: string; next_retry_at?: string }>> => {
  const response = await apiClient.post(`/api/v1/jobs/daily-runner/${execution_id}/retry`);
  return response as unknown as ApiResponse<{ success: boolean; message: string; execution_id: string; next_retry_at?: string }>;
};
