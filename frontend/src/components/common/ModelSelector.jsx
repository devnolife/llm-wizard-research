import { useState, useEffect, useRef } from 'react'
import { Cpu, ChevronDown, Check } from 'lucide-react'
import api from '../../services/api'

const ModelSelector = () => {
  const [models, setModels] = useState([])
  const [current, setCurrent] = useState('')
  const [open, setOpen] = useState(false)
  const [switching, setSwitching] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    api.get('/api/models').then(res => {
      setModels(res.data.models || [])
      setCurrent(res.data.current || '')
    }).catch(() => {})
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
    setSwitching(true)
    try {
      await api.post('/api/models/switch', { model_name: name })
      setCurrent(name)
    } catch (e) {
      console.error('Failed to switch model:', e)
    } finally {
      setSwitching(false)
      setOpen(false)
    }
  }

  const shortName = (name) => {
    if (!name) return 'Model'
    return name.replace(':latest', '').split(':')[0]
  }

  if (models.length === 0) return null

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium border bg-secondary/50 hover:bg-secondary transition-colors text-muted-foreground hover:text-foreground"
      >
        <Cpu className="w-3.5 h-3.5" />
        <span className="hidden sm:inline max-w-[100px] truncate">{shortName(current)}</span>
        <ChevronDown className="w-3 h-3" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-64 rounded-lg border bg-popover shadow-lg z-50 py-1">
          <div className="px-3 py-1.5 text-xs font-semibold text-muted-foreground border-b mb-1">
            Ollama Models
          </div>
          {models.filter(m => !m.name.includes('embed')).map(m => (
            <button
              key={m.name}
              onClick={() => handleSwitch(m.name)}
              disabled={switching}
              className={`w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-secondary/60 transition-colors ${
                m.name === current ? 'text-foreground font-medium' : 'text-muted-foreground'
              }`}
            >
              <div className="flex flex-col items-start">
                <span className="truncate">{shortName(m.name)}</span>
                {m.size && <span className="text-[10px] text-muted-foreground/70">{m.size}</span>}
              </div>
              {m.name === current && <Check className="w-4 h-4 text-green-500" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default ModelSelector
