import { useState, useEffect, useRef, useCallback } from 'react'
import { Loader, Share2 } from 'lucide-react'
import api from '../../../services/api'

const KnowledgeGraphTab = ({ jobId }) => {
  const canvasRef = useRef(null)
  const [kgData, setKgData] = useState(null)
  const [kgLoading, setKgLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api.get('/api/kg/graph', { params: { job_id: jobId } })
      .then(res => { if (!cancelled) setKgData(res.data) })
      .catch(() => { if (!cancelled) setKgData({ nodes: [], edges: [], stats: { total_nodes: 0, total_edges: 0 } }) })
      .finally(() => { if (!cancelled) setKgLoading(false) })
    return () => { cancelled = true }
  }, [jobId])

  const drawGraph = useCallback(() => {
    if (!kgData || !canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const { nodes, edges } = kgData
    if (!nodes.length) return

    const W = canvas.parentElement.offsetWidth || 800
    const H = 500
    canvas.width = W * 2
    canvas.height = H * 2
    canvas.style.width = W + 'px'
    canvas.style.height = H + 'px'
    ctx.scale(2, 2)

    const colors = {
      entity: '#3b82f6', paper: '#10b981', METHOD: '#8b5cf6',
      DOMAIN: '#f59e0b', FINDING: '#ef4444', default: '#6b7280'
    }

    const positions = nodes.map((_, i) => {
      const angle = (2 * Math.PI * i) / nodes.length
      const r = Math.min(W, H) * 0.35
      return { x: W / 2 + r * Math.cos(angle), y: H / 2 + r * Math.sin(angle) }
    })
    const nodeMap = {}
    nodes.forEach((n, i) => { nodeMap[n.id] = i })

    ctx.clearRect(0, 0, W, H)

    edges.forEach(e => {
      const si = nodeMap[e.source]
      const ti = nodeMap[e.target]
      if (si === undefined || ti === undefined) return
      ctx.beginPath()
      ctx.moveTo(positions[si].x, positions[si].y)
      ctx.lineTo(positions[ti].x, positions[ti].y)
      ctx.strokeStyle = '#d1d5db'
      ctx.lineWidth = 0.5
      ctx.stroke()
    })

    nodes.forEach((n, i) => {
      const { x, y } = positions[i]
      const type = n.entity_type || n.node_type || 'default'
      const col = colors[type] || colors.default
      ctx.beginPath()
      ctx.arc(x, y, 5, 0, Math.PI * 2)
      ctx.fillStyle = col
      ctx.fill()
      ctx.font = '9px sans-serif'
      ctx.fillStyle = '#374151'
      const label = (n.name || n.title || n.id || '').substring(0, 20)
      ctx.fillText(label, x + 7, y + 3)
    })
  }, [kgData])

  useEffect(() => { drawGraph() }, [drawGraph])

  if (kgLoading) return <div className="flex items-center gap-2 p-8"><Loader className="w-5 h-5 animate-spin" /> Memuat graf...</div>

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold">{kgData?.stats?.total_nodes || 0}</p>
          <p className="text-xs text-muted-foreground">Node</p>
        </div>
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold">{kgData?.stats?.total_edges || 0}</p>
          <p className="text-xs text-muted-foreground">Relasi</p>
        </div>
        <div className="rounded-lg border bg-card p-4 text-center">
          <p className="text-2xl font-bold">{new Set((kgData?.nodes || []).map(n => n.entity_type || n.node_type || 'unknown')).size}</p>
          <p className="text-xs text-muted-foreground">Jenis Entitas</p>
        </div>
      </div>

      <div className="rounded-lg border bg-card overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center gap-2">
          <Share2 className="w-4 h-4" />
          <span className="font-medium text-sm">Visualisasi Graf Pengetahuan</span>
        </div>
        {kgData?.nodes?.length ? (
          <div className="p-2">
            <canvas ref={canvasRef} className="w-full rounded" />
            <div className="flex gap-4 mt-3 px-2 flex-wrap">
              {Object.entries({ paper: '#10b981', METHOD: '#8b5cf6', DOMAIN: '#f59e0b', FINDING: '#ef4444', entity: '#3b82f6' }).map(([k, c]) => (
                <div key={k} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />
                  {k}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="p-8 text-center text-muted-foreground">
            <p className="text-sm">Belum ada data graf pengetahuan. Jalankan analisis dulu.</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default KnowledgeGraphTab
