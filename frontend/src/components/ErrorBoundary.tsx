/**
 * components/ErrorBoundary.tsx — Complete file.
 * Fixed: ErrorInfo and ReactNode must use `import type` (verbatimModuleSyntax)
 */
import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { RefreshCw, AlertTriangle } from 'lucide-react'

interface Props { children: ReactNode; fallback?: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (!this.state.hasError) return this.props.children
    if (this.props.fallback)  return this.props.fallback

    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-900/20 border border-red-800/40 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <AlertTriangle size={28} className="text-red-400" />
          </div>
          <h1 className="text-white text-xl font-bold mb-2">Something went wrong</h1>
          <p className="text-gray-500 text-sm mb-6">
            An unexpected error occurred. This has been logged.
          </p>
          {this.state.error && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 mb-6 text-left">
              <p className="text-red-400 text-xs font-mono break-all">
                {this.state.error.message}
              </p>
            </div>
          )}
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors"
            >
              <RefreshCw size={14} /> Try Again
            </button>
            <button
              onClick={() => { window.location.href = '/' }}
              className="border border-gray-700 hover:border-gray-500 text-gray-400 hover:text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-colors"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
