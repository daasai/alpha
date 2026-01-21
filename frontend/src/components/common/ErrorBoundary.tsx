/**
 * Error Boundary Component
 * Enhanced version: Shows error ID and improved error handling
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import { formatErrorForDisplay, reportError } from '../../utils/errorHandler';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State;
  public props: Props;

  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
    this.props = props;
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // 上报错误
    reportError(error, {
      componentStack: errorInfo.componentStack,
    });
    
    this.setState({
      errorInfo,
    });
  }

  handleReload = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const errorDisplay = formatErrorForDisplay(
        this.state.error || new Error('Unknown error')
      );

      return (
        <div className="flex items-center justify-center h-full p-8">
          <div className="text-center max-w-md">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">出现错误</h2>
            <p className="text-gray-600 mb-2">{errorDisplay.message}</p>
            {errorDisplay.errorId && (
              <p className="text-sm text-gray-500 mb-4">
                错误ID: <code className="bg-gray-100 px-2 py-1 rounded">{errorDisplay.errorId}</code>
              </p>
            )}
            {errorDisplay.showDetails && this.state.error && (
              <details className="text-left mb-4 bg-gray-100 p-4 rounded text-sm">
                <summary className="cursor-pointer font-medium mb-2">错误详情</summary>
                <pre className="whitespace-pre-wrap text-xs overflow-auto">
                  {this.state.error.stack}
                </pre>
                {this.state.errorInfo && (
                  <div className="mt-2">
                    <strong>Component Stack:</strong>
                    <pre className="whitespace-pre-wrap text-xs overflow-auto mt-1">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </div>
                )}
              </details>
            )}
            <button
              onClick={this.handleReload}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              刷新页面
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
