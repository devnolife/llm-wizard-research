import { NavLink, useNavigate } from 'react-router-dom'
import { Moon, Sun, Upload, Search, MessageSquare, Database } from 'lucide-react'
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
    <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center px-6">
        {/* Logo */}
        <button
          onClick={() => navigate('/')}
          className="mr-6 flex items-center gap-2 font-semibold"
        >
          <span className="text-lg">Research Wizard</span>
        </button>

        {/* Nav Links */}
        <div className="flex items-center gap-1 flex-1">
          {NAV_LINKS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-secondary text-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span className="hidden md:inline">{label}</span>
            </NavLink>
          ))}
        </div>

        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          className="inline-flex items-center justify-center rounded-md w-9 h-9 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </nav>
  )
}

export default Navbar
