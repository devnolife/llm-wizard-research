import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { Share2, RefreshCw, Search, X, Loader } from 'lucide-react'
import { useDarkMode } from '../../contexts/DarkModeContext'
import { useToast } from '../../contexts/ToastContext'

// VOSviewer cluster palette
const CLUSTER_COLORS = [
  '#d62728', // red
  '#2ca02c', // green
  '#1f77b4', // blue
  '#bcbd22', // yellow-olive
  '#9467bd', // purple
  '#17becf', // cyan
  '#ff7f0e', // orange
  '#e377c2', // pink
  '#8c564b', // brown
  '#7f7f7f', // gray
]

const clusterColor = (cluster) => CLUSTER_COLORS[cluster % CLUSTER_COLORS.length]

const GraphPage = () => {
  const { darkMode } = useDarkMode()
  const toast = useToast()
  const fgRef = useRef()
  const containerRef = useRef()

  const [data, setData] = useState({ nodes: [], links: [] })
  const [clusters, setClusters] = useState([])
  const [stats, setStats] = useState(null)
  const [source, setSource] = useState('')
  const [loading, setLoading] = useState(true)
  const [minDegree, setMinDegree] = useState(1)
  const [search, setSearch] = useState('')
  const [selectedNode, setSelectedNode] = useState(null)
  const [showLabels, setShowLabels] = useState(true)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  const fetchGraph = useCallback(async (degree = minDegree) => {
    setLoading(true)
    try {
      const API_BASE = import.meta.env.VITE_API_URL || ''
      const res = await fetch(`${API_BASE}/api/graph?min_degree=${degree}&max_nodes=300`)
      const d = await res.json()
      // react-force-graph mutates objects; give it fresh copies
      setData({
        nodes: d.nodes.map(n => ({ ...n })),
        links: d.links.map(l => ({ ...l })),
      })
      setClusters(d.clusters || [])
      setStats(d.stats || null)
      setSource(d.source || '')
      if (!d.nodes.length) toast.info('Knowledge graph kosong — jalankan analisis atau eksperimen dulu')
    } catch {
      toast.error('Gagal memuat knowledge graph')
    } finally {
      setLoading(false)
    }
  }, [minDegree, toast])

  useEffect(() => { fetchGraph() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Responsive canvas size
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth,
          height: Math.max(480, window.innerHeight - 220),
        })
      }
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [])

  // Spread clusters once data loads
  useEffect(() => {
    if (fgRef.current && data.nodes.length) {
      fgRef.current.d3Force('charge').strength(-120)
      setTimeout(() => fgRef.current?.zoomToFit(600, 60), 700)
    }
  }, [data])

  const searchLower = search.trim().toLowerCase()
  const matchedIds = useMemo(() => {
    if (!searchLower) return null
    return new Set(data.nodes.filter(n => n.label.toLowerCase().includes(searchLower)).map(n => n.id))
  }, [searchLower, data.nodes])

  const neighborIds = useMemo(() => {
    if (!selectedNode) return null
    const ids = new Set([selectedNode.id])
    data.links.forEach(l => {
      const s = typeof l.source === 'object' ? l.source.id : l.source
      const t = typeof l.target === 'object' ? l.target.id : l.target
      if (s === selectedNode.id) ids.add(t)
      if (t === selectedNode.id) ids.add(s)
    })
    return ids
  }, [selectedNode, data.links])

  const maxWeight = useMemo(
    () => Math.max(1, ...data.nodes.map(n => n.weight || 1)),
    [data.nodes]
  )

  // VOSviewer-style node: filled circle + label under for big nodes
  const drawNode = useCallback((node, ctx, globalScale) => {
    const r = 3 + 9 * Math.sqrt((node.weight || 1) / maxWeight)
    const dimmed =
      (matchedIds && !matchedIds.has(node.id)) ||
      (neighborIds && !neighborIds.has(node.id))
    const color = clusterColor(node.cluster)

    ctx.globalAlpha = dimmed ? 0.12 : 0.92
    // Halo
    ctx.beginPath()
    ctx.arc(node.x, node.y, r + 1.6, 0, 2 * Math.PI)
    ctx.fillStyle = darkMode ? '#0b0f19' : '#ffffff'
    ctx.fill()
    // Body
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    // Label — VOSviewer shows labels for prominent nodes, more as you zoom in
    const showThis =
      showLabels &&
      !dimmed &&
      (node.weight >= maxWeight * 0.25 || globalScale > 2.2 || selectedNode?.id === node.id)
    if (showThis) {
      const fontSize = Math.max(2.2, Math.min(5.5, 2 + r * 0.45))
      ctx.font = `${selectedNode?.id === node.id ? 'bold ' : ''}${fontSize}px Inter, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      const label = node.label.length > 28 ? node.label.slice(0, 26) + '…' : node.label
      ctx.lineWidth = fontSize / 4
      ctx.strokeStyle = darkMode ? 'rgba(11,15,25,0.85)' : 'rgba(255,255,255,0.85)'
      ctx.strokeText(label, node.x, node.y + r + 1)
      ctx.fillStyle = darkMode ? '#e5e7eb' : '#1f2937'
      ctx.fillText(label, node.x, node.y + r + 1)
    }
    ctx.globalAlpha = 1
  }, [maxWeight, matchedIds, neighborIds, showLabels, selectedNode, darkMode])

  const linkColor = useCallback((link) => {
    const s = typeof link.source === 'object' ? link.source.id : link.source
    const t = typeof link.target === 'object' ? link.target.id : link.target
    const dimmed =
      (neighborIds && !(neighborIds.has(s) && neighborIds.has(t))) ||
      (matchedIds && !(matchedIds.has(s) || matchedIds.has(t)))
    if (dimmed) return darkMode ? 'rgba(100,116,139,0.05)' : 'rgba(148,163,184,0.06)'
    return darkMode ? 'rgba(148,163,184,0.28)' : 'rgba(100,116,139,0.25)'
  }, [neighborIds, matchedIds, darkMode])

  return (
    <div className="max-w-[1600px] mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Share2 className="w-7 h-7" />
            Knowledge Graph
          </h1>
          <p className="text-muted-foreground mt-1">
            Peta jaringan entitas SPO ala VOSviewer — warna = cluster, ukuran = jumlah koneksi
          </p>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
            <strong>Cara membaca:</strong> Setiap titik adalah konsep (metode, model, atau temuan) yang diekstrak dari paper.
            Garis menghubungkan konsep yang saling berkaitan. Titik besar = konsep yang sering muncul.
            Warna sama = kelompok topik yang sama. <strong>Klik titik</strong> untuk fokus ke konsep dan tetangganya.
          </p>
        </div>
        {stats && (
          <div className="flex gap-3 text-sm">
            <span className="px-3 py-1.5 rounded-md bg-secondary">{stats.nodes} node</span>
            <span className="px-3 py-1.5 rounded-md bg-secondary">{stats.links} relasi</span>
            <span className="px-3 py-1.5 rounded-md bg-secondary">{stats.facts} fakta</span>
            <span className="px-3 py-1.5 rounded-md bg-secondary">{stats.clusters} cluster</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Cari entitas (mis. CNN, BERT)..."
            className="pl-9 pr-8 py-2 w-64 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2">
              <X className="w-4 h-4 text-muted-foreground hover:text-foreground" />
            </button>
          )}
        </div>

        <label className="flex items-center gap-2 text-sm">
          Min. koneksi
          <select
            value={minDegree}
            onChange={e => { const v = +e.target.value; setMinDegree(v); fetchGraph(v) }}
            className="px-2 py-1.5 rounded-md border bg-background"
          >
            {[1, 2, 3, 5].map(v => <option key={v} value={v}>{v}</option>)}
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input type="checkbox" checked={showLabels} onChange={e => setShowLabels(e.target.checked)} />
          Label
        </label>

        <button
          onClick={() => fetchGraph()}
          className="flex items-center gap-2 px-3 py-2 rounded-md border text-sm hover:bg-secondary transition-colors"
        >
          <RefreshCw className="w-4 h-4" /> Segarkan
        </button>

        {selectedNode && (
          <button
            onClick={() => setSelectedNode(null)}
            className="flex items-center gap-2 px-3 py-2 rounded-md bg-secondary text-sm"
          >
            <X className="w-4 h-4" /> {selectedNode.label.slice(0, 30)}
          </button>
        )}

        <span className="text-xs text-muted-foreground ml-auto">sumber: {source}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-4">
        {/* Canvas */}
        <div
          ref={containerRef}
          className={`relative rounded-xl border overflow-hidden ${darkMode ? 'bg-[#0b0f19]' : 'bg-white'}`}
        >
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/60 backdrop-blur-sm">
              <Loader className="w-8 h-8 animate-spin text-primary" />
            </div>
          )}
          {!loading && !data.nodes.length ? (
            <div className="h-[480px] flex flex-col items-center justify-center text-muted-foreground gap-2">
              <Share2 className="w-10 h-10" />
              <p>Belum ada data graph. Unggah & analisis paper, atau jalankan eksperimen.</p>
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              graphData={data}
              width={dimensions.width}
              height={dimensions.height}
              backgroundColor={darkMode ? '#0b0f19' : '#ffffff'}
              nodeCanvasObject={drawNode}
              nodePointerAreaPaint={(node, color, ctx) => {
                const r = 3 + 9 * Math.sqrt((node.weight || 1) / maxWeight)
                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI)
                ctx.fill()
              }}
              linkColor={linkColor}
              linkWidth={l => 0.4 + Math.min(2.4, (l.weight || 1) * 0.5)}
              linkCurvature={0.18}
              onNodeClick={node => setSelectedNode(prev => (prev?.id === node.id ? null : node))}
              onBackgroundClick={() => setSelectedNode(null)}
              cooldownTicks={120}
              d3VelocityDecay={0.25}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="rounded-xl border p-4">
            <h3 className="font-semibold mb-3 text-sm">Cluster</h3>
            <div className="space-y-2.5 max-h-[320px] overflow-y-auto pr-1">
              {clusters.map(c => (
                <div key={c.id} className="flex items-start gap-2.5">
                  <span
                    className="w-3.5 h-3.5 rounded-full mt-0.5 shrink-0"
                    style={{ backgroundColor: clusterColor(c.id) }}
                  />
                  <div className="text-xs leading-snug">
                    <span className="font-medium">Cluster {c.id + 1}</span>
                    <span className="text-muted-foreground"> · {c.size} node</span>
                    <p className="text-muted-foreground mt-0.5">{c.top_terms.join(', ')}</p>
                  </div>
                </div>
              ))}
              {!clusters.length && <p className="text-xs text-muted-foreground">—</p>}
            </div>
          </div>

          {selectedNode && (
            <div className="rounded-xl border p-4">
              <h3 className="font-semibold mb-2 text-sm break-words">{selectedNode.label}</h3>
              <dl className="text-xs space-y-1.5">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Tipe</dt>
                  <dd className="font-medium">{selectedNode.type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Koneksi</dt>
                  <dd className="font-medium">{selectedNode.weight}</dd>
                </div>
                <div className="flex justify-between items-center">
                  <dt className="text-muted-foreground">Cluster</dt>
                  <dd className="flex items-center gap-1.5 font-medium">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: clusterColor(selectedNode.cluster) }}
                    />
                    {selectedNode.cluster + 1}
                  </dd>
                </div>
              </dl>
              <p className="text-[11px] text-muted-foreground mt-3">
                Klik node lain untuk fokus, klik area kosong untuk reset.
              </p>
            </div>
          )}

          <div className="rounded-xl border p-4 text-xs text-muted-foreground leading-relaxed">
            <p><b className="text-foreground">Scroll</b> = zoom · <b className="text-foreground">drag</b> = geser</p>
            <p className="mt-1">Ukuran node ∝ jumlah relasi SPO. Warna mengikuti komunitas (modularity clustering), seperti tampilan network VOSviewer.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GraphPage
