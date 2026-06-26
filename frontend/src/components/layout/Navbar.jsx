import { NavLink, useNavigate } from 'react-router-dom'
import { Moon, Sun, Upload, Search, MessageSquare, Database, FileText, Share2, Sparkles } from 'lucide-react'
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
    <nav className="sticky top-0 z-50 border-b border-border/60 glass">
      <div className="w-full flex h-16 items-center px-5 lg:px-10">
        {/* Logo */}
        <button
          onClick={() => navigate('/')}
          className="group mr-7 flex items-center gap-2.5"
          aria-label="Beranda Wizard Research"
        >
          <span className="relative grid h-9 w-9 place-items-center rounded-xl bg-primary text-primary-foreground shadow-glow transition-transform duration-300 group-hover:scale-105 group-hover:-rotate-3">
            <Sparkles className="h-[18px] w-[18px]" />
            <span className="absolute inset-0 rounded-xl ring-1 ring-inset ring-white/20" />
          </span>
          <span className="flex flex-col leading-none text-left">
            <span className="font-display text-[15px] font-bold tracking-tight">Wizard Research</span>
            <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Synthesis Gap Detection
            </span>
          </span>
        </button>

        {/* Nav Links */}
        <div className="flex items-center gap-0.5 flex-1">
          {NAV_LINKS.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                title={item.desc}
                className={({ isActive }) =>
                  `group relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${isActive
                    ? 'text-primary bg-primary/10 ring-1 ring-inset ring-primary/20'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                  }`
                }
              >
                <Icon className="h-4 w-4 transition-transform duration-200 group-hover:scale-110" />
                <span className="hidden md:inline">{item.label}</span>
              </NavLink>
            )
          })}
        </div>

        {/* Model Selector */}
        <ModelSelector />

        {/* Dark Mode Toggle */}
        <button
          onClick={toggleDarkMode}
          aria-label={darkMode ? 'Mode terang' : 'Mode gelap'}
          className="ml-1.5 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-border/60 text-muted-foreground transition-all duration-200 hover:border-primary/40 hover:text-foreground hover:bg-secondary"
        >
          {darkMode ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </button>
      </div>
    </nav>
  )
}

export default Navbar
