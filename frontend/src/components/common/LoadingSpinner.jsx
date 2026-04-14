import { motion } from 'framer-motion'
import { Loader } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'

const LoadingSpinner = ({ message = 'Loading...', size = 'lg' }) => {
  const { darkMode } = useDarkMode()

  const sizes = {
    sm: { icon: 'w-8 h-8', text: 'text-sm' },
    md: { icon: 'w-12 h-12', text: 'text-base' },
    lg: { icon: 'w-20 h-20', text: 'text-lg' },
  }

  const s = sizes[size] || sizes.lg

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-12">
      <motion.div className="relative">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <Loader className={`${s.icon} ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
        </motion.div>
        <motion.div
          className="absolute inset-0 blur-2xl"
          animate={{ opacity: [0.3, 0.6, 0.3], scale: [1, 1.2, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Loader className={`${s.icon} ${darkMode ? 'text-blue-400' : 'text-blue-600'}`} />
        </motion.div>
      </motion.div>
      {message && (
        <p className={`${s.text} font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          {message}
        </p>
      )}
    </div>
  )
}

export default LoadingSpinner
