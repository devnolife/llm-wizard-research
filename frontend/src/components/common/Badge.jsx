import { useDarkMode } from '../../contexts/DarkModeContext'

const BADGE_VARIANTS = {
  success: {
    dark: 'bg-green-500/10 text-green-400 border-green-500/30',
    light: 'bg-green-50 text-green-700 border-green-200',
  },
  error: {
    dark: 'bg-red-500/10 text-red-400 border-red-500/30',
    light: 'bg-red-50 text-red-700 border-red-200',
  },
  warning: {
    dark: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
    light: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  },
  info: {
    dark: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
    light: 'bg-blue-50 text-blue-700 border-blue-200',
  },
  default: {
    dark: 'bg-gray-500/10 text-gray-400 border-gray-500/30',
    light: 'bg-gray-100 text-gray-700 border-gray-200',
  },
}

const Badge = ({ children, variant = 'default', className = '' }) => {
  const { darkMode } = useDarkMode()
  const colors = BADGE_VARIANTS[variant] || BADGE_VARIANTS.default
  const colorClass = darkMode ? colors.dark : colors.light

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold border ${colorClass} ${className}`}>
      {children}
    </span>
  )
}

export default Badge
