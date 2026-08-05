import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useState, useRef, useEffect } from 'react'
import {
  Moon, Sun, Upload, Search, MessageSquare, Database, FileText, Share2,
  Sparkles, MoreHorizontal, ChevronDown,
} from 'lucide-react'
import useDarkMode from '../../hooks/useDarkMode'
import ModelSelector from '../common/ModelSelector'

// Alur utama: unggah jurnal → lihat gap → cari jurnal pendukung.
// Menu lain tetap ada, tetapi disembunyikan di "Lainnya" agar tidak membingungkan.
const PRIMARY_LINKS = [
  { to: '/', label: 'Unggah', icon: Upload, desc: 'Unggah paper PDF untuk dianalisis otomatis (topik, gap, rekomendasi)' },
  { to: '/search', label: 'Cari Jurnal', icon: Search, desc: 'Cari paper pendukung berdasarkan kata kunci' },
]

const MORE_LINKS = [
  { to: '/chat', label: 'Chat', icon: MessageSquare, desc: 'Tanya jawab dengan AI tentang paper yang sudah diunggah' },
  { to: '/documents', label: 'Dokumen', icon: Database, desc: 'Daftar semua paper yang tersimpan di database' },
  { to: '/graph', label: 'Graf', icon: Share2, desc: 'Peta visual hubungan antar konsep dari semua paper' },
  { to: '/revisi', label: 'Revisi', icon: FileText, desc: 'Catatan revisi proposal tesis' },
]

const Navbar = () => {
  const { darkMode, toggleDarkMode } = useDarkMode()
  const navigate = useNavigate()
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const moreRef = useRef(null)

  const moreActive = MORE_LINKS.some((item) => location.pathname.startsWith(item.to))

  useEffect(() => {
    const onClickOutside = (e) => {
      if (moreRef.current && !moreRef.current.contains(e.target)) setMoreOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

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

        {/* Nav utama */}
        <div className="flex items-center gap-0.5 flex-1">
          {PRIMARY_LINKS.map((item) => {
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

          {/* Dropdown "Lainnya" — fitur pendukung, tersembunyi dari alur utama */}
          <div className="relative" ref={moreRef}>
            <button
              onClick={() => setMoreOpen((open) => !open)}
              aria-haspopup="menu"
              aria-expanded={moreOpen}
              title="Menu tambahan (chat, dokumen, graf, revisi)"
              className={`group relative flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 ${moreActive
                ? 'text-primary bg-primary/10 ring-1 ring-inset ring-primary/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                }`}
            >
              <MoreHorizontal className="h-4 w-4" />
              <span className="hidden md:inline">Lainnya</span>
              <ChevronDown className={`h-3 w-3 transition-transform ${moreOpen ? 'rotate-180' : ''}`} />
            </button>
            {moreOpen && (
              <div
                role="menu"
                className="absolute left-0 top-full mt-1.5 w-56 rounded-xl border border-border/70 bg-card p-1.5 shadow-lg"
              >
                {MORE_LINKS.map((item) => {
                  const Icon = item.icon
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      role="menuitem"
                      title={item.desc}
                      onClick={() => setMoreOpen(false)}
                      className={({ isActive }) =>
                        `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${isActive
                          ? 'text-primary bg-primary/10'
                          : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                        }`
                      }
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  )
                })}
              </div>
            )}
          </div>
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
