import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-canvas flex items-center justify-center px-6">
          <div className="max-w-md text-center">
            <div className="w-14 h-14 rounded-xl gradient-orange flex items-center justify-center shadow-orange mx-auto mb-5">
              <span className="text-white text-2xl font-extrabold font-mono">!</span>
            </div>
            <h1 className="text-h3 text-ink-primary font-mono mb-2">Something went wrong</h1>
            <p className="text-small text-ink-secondary mb-6">
              An unexpected error occurred. Try refreshing the page. If the problem
              persists, contact your system administrator.
            </p>
            <pre className="bg-surface-2 border border-border-subtle rounded-lg p-4 text-[11px] text-ink-muted font-mono text-left overflow-x-auto mb-6">
              {this.state.error?.message}
            </pre>
            <button
              onClick={() => window.location.reload()}
              className="btn btn-primary btn-lg"
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
