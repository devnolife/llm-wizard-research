import { motion } from 'framer-motion'
import { NavLink, useNavigate } from 'react-router-dom'
import { Moon, Sun, Sparkles, Zap, Upload, Search, MessageSquare, Database } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'

const NAV_LINKS = [
  { to: '/', label: 'Upload', icon: Upload },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/documents', label: 'Documents', icon: Database },
]

const Navbar = () => {
  const { darkMode, toggleDarkMode } = useDarkMode()
  const navigate = useNavigate()

  return (
    <motion.nav
      initial={{ y: -100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: "spring", stiffness: 100, damping: 20 }}
      className={`sticky top-0 z-50 ${
        darkMode
          ? 'bg-gray-900/40 border-gray-700/50'
          : 'bg-white/40 border-white/80'
      } border-b backdrop-blur-xl shadow-lg`}
      style={{
        backdropFilter: 'blur(20px) saturate(180%)',
        WebkitBackdropFilter: 'blur(20px) saturate(180%)'
      }}
    >
      <div className="container mx-auto px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div
            className="flex items-center space-x-3 group cursor-pointer"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => navigate('/')}
          >
            <motion.div
              className={`relative p-2.5 rounded-xl ${
                darkMode
                  ? 'bg-gradient-to-br from-blue-500/20 to-purple-500/20'
                  : 'bg-gradient-to-br from-blue-500/10 to-purple-500/10'
              } shadow-lg`}
              whileHover={{ rotate: [0, -10, 10, 0] }}
              transition={{ duration: 0.5 }}
            >
              <Sparkles className={`w-6 h-6 ${
                darkMode ? 'text-blue-400' : 'text-blue-600'
              }`} />
              <motion.div
                className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>
            <div className="hidden sm:block">
              <h1 className={`text-xl font-bold bg-gradient-to-r ${
                darkMode
                  ? 'from-blue-400 via-purple-400 to-pink-400'
                  : 'from-blue-600 via-purple-600 to-pink-600'
              } bg-clip-text text-transparent`}>
                Research Wizard
              </h1>
              <p className={`text-[10px] flex items-center gap-1 ${
                darkMode ? 'text-gray-400' : 'text-gray-600'
              }`}>
                <Zap className="w-2.5 h-2.5" />
                AI-Powered Research Analysis
              </p>
            </div>
          </motion.div>

          {/* Navigation Links */}
          <div className="flex items-center gap-1">
            {NAV_LINKS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? darkMode
                        ? 'bg-blue-600/20 text-blue-400'
                        : 'bg-blue-50 text-blue-700'
                      : darkMode
                        ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  }`
                }
              >
                <Icon className="w-4 h-4" />
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </div>

          {/* Dark Mode Toggle */}
          <motion.button
            whileHover={{ scale: 1.1, rotate: 10 }}
            whileTap={{ scale: 0.9 }}
            onClick={toggleDarkMode}
            className={`relative p-3 rounded-xl transition-all duration-300 ${
              darkMode
                ? 'bg-gradient-to-br from-amber-500/20 to-orange-500/20 text-amber-400 hover:from-amber-500/30 hover:to-orange-500/30'
                : 'bg-gradient-to-br from-indigo-500/20 to-purple-500/20 text-indigo-600 hover:from-indigo-500/30 hover:to-purple-500/30'
            } shadow-lg`}
          >
            <motion.div
              initial={false}
              animate={{ rotate: darkMode ? 180 : 0 }}
              transition={{ duration: 0.5, type: "spring" }}
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </motion.div>
          </motion.button>
        </div>
      </div>
    </motion.nav>
  )
}

export default Navbar
