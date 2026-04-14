import { motion } from 'framer-motion'
import { useDarkMode } from '../../contexts/DarkModeContext'

const EmptyState = ({ icon: Icon, title, description, action, actionLabel }) => {
  const { darkMode } = useDarkMode()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center py-16 px-4 text-center"
    >
      {Icon && (
        <motion.div
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className={`p-6 rounded-3xl mb-6 ${
            darkMode
              ? 'bg-gradient-to-br from-gray-700/50 to-gray-800/50'
              : 'bg-gradient-to-br from-gray-100 to-gray-200'
          }`}
        >
          <Icon className={`w-12 h-12 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`} />
        </motion.div>
      )}
      <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        {title}
      </h3>
      <p className={`text-sm max-w-sm mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
        {description}
      </p>
      {action && (
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={action}
          className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-lg"
        >
          {actionLabel || 'Get Started'}
        </motion.button>
      )}
    </motion.div>
  )
}

export default EmptyState
