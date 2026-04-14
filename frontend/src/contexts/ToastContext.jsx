import { createContext, useContext, useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from 'lucide-react'

const ToastContext = createContext()

const TOAST_ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const TOAST_COLORS = {
  success: {
    dark: 'bg-green-500/10 border-green-500/50 text-green-400',
    light: 'bg-green-50 border-green-300 text-green-700',
    icon: 'text-green-500',
  },
  error: {
    dark: 'bg-red-500/10 border-red-500/50 text-red-400',
    light: 'bg-red-50 border-red-300 text-red-700',
    icon: 'text-red-500',
  },
  warning: {
    dark: 'bg-yellow-500/10 border-yellow-500/50 text-yellow-400',
    light: 'bg-yellow-50 border-yellow-300 text-yellow-700',
    icon: 'text-yellow-500',
  },
  info: {
    dark: 'bg-blue-500/10 border-blue-500/50 text-blue-400',
    light: 'bg-blue-50 border-blue-300 text-blue-700',
    icon: 'text-blue-500',
  },
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
    if (duration > 0) {
      setTimeout(() => removeToast(id), duration)
    }
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
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

const ToastContainer = ({ toasts, onRemove }) => {
  const isDark = document.documentElement.classList.contains('dark')

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-3 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map(({ id, message, type }) => {
          const Icon = TOAST_ICONS[type]
          const colors = TOAST_COLORS[type]
          const colorClass = isDark ? colors.dark : colors.light

          return (
            <motion.div
              key={id}
              initial={{ opacity: 0, x: 100, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 200, damping: 20 }}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border backdrop-blur-xl shadow-xl ${colorClass}`}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${colors.icon}`} />
              <p className="text-sm font-medium flex-1">{message}</p>
              <button
                onClick={() => onRemove(id)}
                className="flex-shrink-0 p-0.5 rounded-lg hover:bg-black/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

export default ToastContext
