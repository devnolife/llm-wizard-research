import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Home, AlertCircle } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'

const NotFoundPage = () => {
  const { darkMode } = useDarkMode()
  const navigate = useNavigate()

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 100 }}
        className="text-center max-w-md"
      >
        <motion.div
          animate={{ y: [0, -10, 0] }}
          transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          className="inline-block mb-8"
        >
          <div className={`p-6 rounded-3xl ${
            darkMode
              ? 'bg-gradient-to-br from-red-500/20 to-orange-500/20'
              : 'bg-gradient-to-br from-red-100 to-orange-100'
          }`}>
            <AlertCircle className={`w-16 h-16 ${darkMode ? 'text-red-400' : 'text-red-500'}`} />
          </div>
        </motion.div>

        <h1 className={`text-7xl font-extrabold mb-4 bg-gradient-to-r ${
          darkMode
            ? 'from-red-400 via-orange-400 to-yellow-400'
            : 'from-red-600 via-orange-600 to-yellow-600'
        } bg-clip-text text-transparent`}>
          404
        </h1>

        <h2 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Page Not Found
        </h2>

        <p className={`text-base mb-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          The page you're looking for doesn't exist or has been moved.
        </p>

        <motion.button
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-2xl shadow-xl"
        >
          <Home className="w-5 h-5" />
          Back to Home
        </motion.button>
      </motion.div>
    </div>
  )
}

export default NotFoundPage
