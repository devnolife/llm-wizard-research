import { NavLink, useNavigate } from 'react-router-dom'
import { Moon, Sun, Upload, Search, MessageSquare, Database, FileText, Share2 } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import ModelSelector from '../common/ModelSelector'

const NAV_LINKS = [
  { to: '/', label: 'Unggah', icon: Upload, desc: 'Unggah paper PDF untuk dianalisis otomatis (topik, gap, rekomendasi)' },
  { to: '/search', label: 'Cari', icon: Search, desc: 'Cari paper di database berdasarkan kata kunci' },
  { to: '/chat', label: 'Chat', icon: MessageSquare, desc: 'Tanya jawab dengan AI tentang paper yang sudah diunggah' },
  { to: '/documents', label: 'Dokumen', icon: Database, desc: 'Daftar semua paper yang tersimpan di database' },
  { to: '/graph', label: 'Graf', icon: Share2, desc: 'Peta visual hubungan antar konsep dari semua paper (gaya VOSviewer)' },
  { to: '/revisi', label: 'Revisi', icon: FileText, desc: 'Catatan revisi proposal tesis' },
]

const Navbar = () => {
  const { darkMode, toggleDarkMode } = useDarkMode()
  const navigate = useNavigate()

  return (
    <nav className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="w-full flex h-14 items-center px-6 lg:px-10">
        {/* Logo */}
        <button
          onClick={() => navigate('/')}
          className="mr-6 flex items-center gap-2 font-semibold"
        >
          <span className="text-lg">Research Wizard</span>
        </button>

        {/* Nav Links */}
        <div className="flex items-center gap-1 flex-1">
          {NAV_LINKS.map(({ to, label, icon: Icon, desc }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              title={desc}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${isActive
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

        {/* Model Selector */}
        <ModelSelector />

        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          className="inline-flex items-center justify-center rounded-md w-9 h-9 text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors ml-1"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </nav>
  )
}

export default Navbar
