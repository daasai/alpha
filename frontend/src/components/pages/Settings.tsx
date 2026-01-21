import { Play, RefreshCw, Clock, CheckCircle, XCircle, AlertCircle, Loader } from 'lucide-react';
import { useTriggerDailyRunner, useDailyRunnerStatus, useDailyRunnerHistory } from '../../hooks/useJobs';
import { useToast } from '../common/Toast';
import type { ExecutionStatus } from '../../api/services/jobs';

const Settings: React.FC = () => {
  const { showToast } = useToast();
  const { trigger, loading: triggerLoading } = useTriggerDailyRunner();
  const { status, loading: statusLoading, refetch: refetchStatus } = useDailyRunnerStatus(undefined, true);
  const { history, loading: historyLoading, refetch: refetchHistory } = useDailyRunnerHistory(undefined, undefined, 20);

  const handleTrigger = async (force: boolean = false) => {
    try {
      const result = await trigger({ force });
      if (result) {
        showToast(`任务已触发，执行ID: ${result.execution_id}`, 'success');
        setTimeout(() => {
          refetchStatus();
          refetchHistory();
        }, 1000);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '触发任务失败';
      showToast(`触发失败: ${errorMsg}`, 'error');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'FAILED':
      case 'TIMEOUT':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'RUNNING':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'RETRYING':
        return <RefreshCw className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'DUPLICATE':
        return <AlertCircle className="w-5 h-5 text-orange-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusText = (status: string) => {
    const statusMap: Record<string, string> = {
      'SUCCESS': '成功',
      'FAILED': '失败',
      'TIMEOUT': '超时',
      'RUNNING': '运行中',
      'RETRYING': '重试中',
      'DUPLICATE': '重复执行',
      'PENDING': '等待中',
      'BLOCKED': '已阻止'
    };
    return statusMap[status] || status;
  };

  const formatDateTime = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return 'N/A';
    if (seconds < 60) return `${seconds.toFixed(1)}秒`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}分钟`;
    return `${(seconds / 3600).toFixed(1)}小时`;
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">系统设置</h1>

        {/* 当前状态卡片 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">当前任务状态</h2>
            <button
              type="button"
              onClick={() => refetchStatus()}
              disabled={statusLoading}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 inline-block mr-1 ${statusLoading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>

          {statusLoading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : status ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                {getStatusIcon(status.status)}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900">{getStatusText(status.status)}</span>
                    {status.is_duplicate && (
                      <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded">重复执行</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    交易日期: {status.trade_date} | 执行ID: {status.execution_id}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-4 border-t border-gray-200">
                <div>
                  <div className="text-xs text-gray-500 mb-1">开始时间</div>
                  <div className="text-sm font-medium">{formatDateTime(status.started_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">完成时间</div>
                  <div className="text-sm font-medium">{formatDateTime(status.completed_at)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">执行时长</div>
                  <div className="text-sm font-medium">{formatDuration(status.duration_seconds)}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-1">重试次数</div>
                  <div className="text-sm font-medium">{status.retry_count}/{status.max_retries}</div>
                </div>
              </div>

              {status.steps_completed && status.steps_completed.length > 0 && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="text-xs text-gray-500 mb-2">已完成步骤</div>
                  <div className="flex flex-wrap gap-2">
                    {status.steps_completed.map((step) => (
                      <span key={step} className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                        {step}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {status.errors && status.errors.length > 0 && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="text-xs text-gray-500 mb-2">错误信息</div>
                  <div className="space-y-1">
                    {status.errors.map((error) => (
                      <div key={error} className="text-sm text-red-600 bg-red-50 p-2 rounded">
                        {error}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">暂无执行记录</div>
          )}
        </div>

        {/* 操作按钮 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">任务操作</h2>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={() => handleTrigger(false)}
              disabled={triggerLoading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4" />
              {triggerLoading ? '触发中...' : '手动触发每日任务'}
            </button>
            <button
              type="button"
              onClick={() => handleTrigger(true)}
              disabled={triggerLoading}
              className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="w-4 h-4" />
              {triggerLoading ? '触发中...' : '强制执行（忽略幂等性检查）'}
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-3">
            手动触发：如果当天已有成功记录，将提示重复执行。强制执行：忽略幂等性检查，强制重新执行。
          </p>
        </div>

        {/* 执行历史 */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">执行历史</h2>
            <button
              type="button"
              onClick={() => refetchHistory()}
              disabled={historyLoading}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 inline-block mr-1 ${historyLoading ? 'animate-spin' : ''}`} />
              刷新
            </button>
          </div>

          {historyLoading ? (
            <div className="text-center py-8 text-gray-500">加载中...</div>
          ) : history && history.executions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">状态</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">交易日期</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">触发类型</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">开始时间</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">执行时长</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">重试</th>
                  </tr>
                </thead>
                <tbody>
                  {history.executions.map((exec: ExecutionStatus) => (
                    <tr key={exec.execution_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(exec.status)}
                          <span className="text-sm">{getStatusText(exec.status)}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-900">{exec.trade_date}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {exec.trigger_type === 'SCHEDULED' ? '定时' : exec.trigger_type === 'API' ? 'API' : '手动'}
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600">{formatDateTime(exec.started_at)}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">{formatDuration(exec.duration_seconds)}</td>
                      <td className="py-3 px-4 text-sm text-gray-600">
                        {exec.retry_count > 0 ? `${exec.retry_count}/${exec.max_retries}` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">暂无执行历史</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Settings;
