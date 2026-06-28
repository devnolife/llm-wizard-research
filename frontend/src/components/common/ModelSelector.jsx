import { useState, useEffect, useRef } from 'react'
import { Cpu, ChevronDown, Check, Loader } from 'lucide-react'
import api from '../../services/api'

const ModelSelector = () => {
  const [models, setModels] = useState([])
  const [current, setCurrent] = useState('')
  const [open, setOpen] = useState(false)
  const [switching, setSwitching] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    api.get('/api/models').then(res => {
      setModels(res.data.models || [])
      setCurrent(res.data.current || '')
    }).catch(() => { })
  }, [])

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleSwitch = async (name) => {
    if (name === current || switching) return
    setSwitching(name)
    try {
      await api.post('/api/models/switch', { model_name: name })
      setCurrent(name)
      setOpen(false)
    } catch (e) {
      console.error('Gagal mengganti model:', e)
    } finally {
      setSwitching('')
    }
  }

  // Rapikan nama model agar mudah dibaca: ambil segmen terakhir & buang penanda teknis
  const displayName = (name) => {
    if (!name) return 'Model'
    let n = name
    if (n.includes('/')) n = n.split('/').pop()   // hf.co/org/Model -> Model
    n = n.replace(/[-_]?GGUF$/i, '')              // buang penanda GGUF
    n = n.split(':')[0]                           // buang tag (:latest, :Q8_0, :27b)
    return n
  }

  if (models.length === 0) return null

  const visibleModels = models.filter(m => !m.name.toLowerCase().includes('embed'))

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        title={current ? `Model aktif: ${current}` : 'Pilih model'}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border bg-secondary/50 hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
      >
        <Cpu className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="hidden sm:inline max-w-[120px] truncate">{displayName(current)}</span>
        <ChevronDown className={`w-3 h-3 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-72 rounded-lg border bg-popover text-popover-foreground shadow-lg z-50 py-1">
          <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground border-b mb-1 flex items-center justify-between">
            <span>Model Ollama</span>
            <span className="text-[10px] font-normal text-muted-foreground/70">{visibleModels.length} model</span>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {visibleModels.map(m => {
              const isActive = m.name === current
              const isSwitching = switching === m.name
              return (
                <button
                  key={m.name}
                  onClick={() => handleSwitch(m.name)}
                  disabled={!!switching}
                  title={m.name}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-secondary/60 transition-colors disabled:opacity-60 ${isActive ? 'bg-secondary/40' : ''
                    }`}
                >
                  <span className={`flex-1 min-w-0 truncate text-left ${isActive ? 'text-foreground font-medium' : 'text-foreground/90'}`}>
                    {displayName(m.name)}
                  </span>
                  {m.size && (
                    <span className="flex-shrink-0 text-[10px] font-medium text-muted-foreground bg-secondary px-1.5 py-0.5 rounded">
                      {m.size}
                    </span>
                  )}
                  {isSwitching
                    ? <Loader className="w-4 h-4 flex-shrink-0 animate-spin text-primary" />
                    : isActive
                      ? <Check className="w-4 h-4 flex-shrink-0 text-green-500" />
                      : <span className="w-4 flex-shrink-0" />}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default ModelSelector
