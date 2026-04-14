import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from 'lucide-react'

const ToastContext = createContext()

const TOAST_ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const TOAST_STYLES = {
  success: 'border-green-500/30 text-green-700 dark:text-green-400',
  error: 'border-destructive/30 text-destructive',
  warning: 'border-yellow-500/30 text-yellow-700 dark:text-yellow-400',
  info: 'border-blue-500/30 text-blue-700 dark:text-blue-400',
}

let toastId = 0

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const addToast = useCallback((message, type = 'info', duration = 5000) => {
    const id = ++toastId
    setToasts(prev => [...prev, { id, message, type }])
    if (duration > 0) setTimeout(() => removeToast(id), duration)
    return id
  }, [removeToast])

  const toast = {
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    warning: (msg, duration) => addToast(msg, 'warning', duration),
    info: (msg, duration) => addToast(msg, 'info', duration),
  }

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map(({ id, message, type }) => (
          <Toast key={id} id={id} message={message} type={type} onRemove={removeToast} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

const Toast = ({ id, message, type, onRemove }) => {
  const Icon = TOAST_ICONS[type]
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
  }, [])

  return (
    <div
      className={`pointer-events-auto flex items-start gap-3 p-3 rounded-lg border bg-card shadow-md transition-all duration-200 ${
        visible ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
      } ${TOAST_STYLES[type]}`}
    >
      <Icon className="w-4 h-4 flex-shrink-0 mt-0.5" />
      <p className="text-sm flex-1">{message}</p>
      <button
        onClick={() => onRemove(id)}
        className="flex-shrink-0 p-0.5 rounded hover:bg-secondary transition-colors text-muted-foreground"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

export default ToastContext
