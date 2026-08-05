// Ilustrasi SVG animasi per langkah proses — supaya orang awam LANGSUNG
// melihat apa yang terjadi, bukan hanya membaca teks.
// Semua animasi memakai SVG <animate> bawaan (tanpa library tambahan).

const C = {
  paper: '#60a5fa',      // biru — jurnal/PDF
  chunk: '#93c5fd',      // biru muda — potongan teks
  fact: '#a78bfa',       // ungu — fakta
  gap: '#f59e0b',        // amber — gap
  rule: '#10b981',       // hijau — aturan/lolos
  reject: '#ef4444',     // merah — ditolak
  line: 'currentColor',
}

const Doc = ({ x, y, w = 34, h = 44, fill = C.paper, delay = '0s', label }) => (
  <g opacity="0">
    <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin={delay} fill="freeze" />
    <rect x={x} y={y} width={w} height={h} rx="3" fill={fill} opacity="0.15" stroke={fill} strokeWidth="1.5" />
    <line x1={x + 6} y1={y + 10} x2={x + w - 6} y2={y + 10} stroke={fill} strokeWidth="2" opacity="0.7" />
    <line x1={x + 6} y1={y + 18} x2={x + w - 6} y2={y + 18} stroke={fill} strokeWidth="2" opacity="0.5" />
    <line x1={x + 6} y1={y + 26} x2={x + w - 10} y2={y + 26} stroke={fill} strokeWidth="2" opacity="0.5" />
    <line x1={x + 6} y1={y + 34} x2={x + w - 14} y2={y + 34} stroke={fill} strokeWidth="2" opacity="0.3" />
    {label && <text x={x + w / 2} y={y + h + 12} textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.6">{label}</text>}
  </g>
)

const FlowArrow = ({ x1, y1, x2, y2, delay = '0s' }) => (
  <g>
    <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="currentColor" strokeWidth="1.5"
      strokeDasharray="4 3" opacity="0.35" />
    <circle r="3" fill={C.gap}>
      <animateMotion dur="1.6s" begin={delay} repeatCount="indefinite"
        path={`M ${x1} ${y1} L ${x2} ${y2}`} />
    </circle>
  </g>
)

// ── 1. PDF masuk → dipecah jadi potongan ───────────────────────────
export const VisualIngest = ({ nPapers = 3, nChunks = 295 }) => (
  <svg viewBox="0 0 340 110" className="w-full max-w-md" role="img"
    aria-label={`${nPapers} PDF dipecah menjadi ${nChunks} potongan teks`}>
    {[0, 1, 2].slice(0, Math.min(nPapers, 3)).map(i => (
      <Doc key={i} x={10 + i * 14} y={18 + i * 6} delay={`${i * 0.25}s`} />
    ))}
    <text x="34" y="100" textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.7">{nPapers} PDF</text>
    <FlowArrow x1={70} y1={45} x2={130} y2={45} delay="0.8s" />
    <text x="100" y="36" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.6">dipecah</text>
    {Array.from({ length: 18 }).map((_, i) => {
      const col = i % 6, row = Math.floor(i / 6)
      return (
        <rect key={i} x={140 + col * 26} y={20 + row * 22} width="20" height="15" rx="2"
          fill={C.chunk} opacity="0">
          <animate attributeName="opacity" from="0" to="0.75" dur="0.3s"
            begin={`${1 + i * 0.07}s`} fill="freeze" />
        </rect>
      )
    })}
    <text x="215" y="100" textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.7">{nChunks} potongan teks (±500 kata)</text>
  </svg>
)

// ── 2. Potongan → fakta Subjek-Hubungan-Objek ─────────────────────
export const VisualFacts = ({ nFacts = 16 }) => (
  <svg viewBox="0 0 340 110" className="w-full max-w-md" role="img"
    aria-label={`Kalimat diubah menjadi ${nFacts} fakta terstruktur`}>
    <rect x="8" y="35" width="78" height="40" rx="3" fill={C.chunk} opacity="0.2" stroke={C.chunk} />
    <line x1="16" y1="47" x2="78" y2="47" stroke={C.chunk} strokeWidth="2" opacity="0.8" />
    <line x1="16" y1="56" x2="70" y2="56" stroke={C.chunk} strokeWidth="2" opacity="0.6" />
    <line x1="16" y1="65" x2="74" y2="65" stroke={C.chunk} strokeWidth="2" opacity="0.6" />
    <text x="47" y="92" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.7">kalimat di jurnal</text>
    <FlowArrow x1={92} y1={55} x2={140} y2={55} delay="0.3s" />
    <text x="116" y="46" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.6">dicatat</text>
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin="0.9s" fill="freeze" />
      <circle cx="170" cy="55" r="17" fill={C.fact} opacity="0.15" stroke={C.fact} strokeWidth="1.5" />
      <text x="170" y="58" textAnchor="middle" fontSize="8" fontWeight="bold" fill="currentColor">CRNN</text>
      <text x="170" y="86" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.6">Subjek</text>
    </g>
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin="1.3s" fill="freeze" />
      <line x1="187" y1="55" x2="235" y2="55" stroke={C.fact} strokeWidth="1.5" markerEnd="url(#arrowF)" />
      <text x="211" y="47" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.8">diterapkan pada</text>
      <text x="211" y="86" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.6">Hubungan</text>
    </g>
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.6s" begin="1.7s" fill="freeze" />
      <circle cx="268" cy="55" r="17" fill={C.fact} opacity="0.15" stroke={C.fact} strokeWidth="1.5" />
      <text x="268" y="53" textAnchor="middle" fontSize="7" fontWeight="bold" fill="currentColor">pengenalan</text>
      <text x="268" y="62" textAnchor="middle" fontSize="7" fontWeight="bold" fill="currentColor">struk</text>
      <text x="268" y="86" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.6">Objek</text>
    </g>
    <text x="320" y="58" textAnchor="middle" fontSize="9" fontWeight="bold" fill={C.fact} opacity="0">
      ×{nFacts}
      <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="2.1s" fill="freeze" />
    </text>
    <defs>
      <marker id="arrowF" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
        <path d="M0,0 L6,3 L0,6" fill="none" stroke={C.fact} strokeWidth="1.5" />
      </marker>
    </defs>
  </svg>
)

// ── 3. Dua jurnal dibandingkan → kontradiksi ──────────────────────
export const VisualCompare = ({ nGaps = 3 }) => (
  <svg viewBox="0 0 340 120" className="w-full max-w-md" role="img"
    aria-label="Fakta antar jurnal dibandingkan dan ditemukan pertentangan">
    <Doc x={20} y={12} fill={C.paper} label="Jurnal A" />
    <Doc x={20} y={12} w={0} h={0} />
    <Doc x={286} y={12} w={34} h={44} fill="#34d399" delay="0.2s" label="Jurnal B" />
    {/* klaim dari masing-masing jurnal bergerak ke tengah */}
    <g>
      <rect x="66" y="28" width="60" height="14" rx="7" fill={C.paper} opacity="0.25">
        <animate attributeName="x" from="66" to="100" dur="1.2s" begin="0.6s" fill="freeze" />
      </rect>
      <text fontSize="7" fill="currentColor" opacity="0.9" y="37" x="96" textAnchor="middle">
        <animate attributeName="x" from="96" to="130" dur="1.2s" begin="0.6s" fill="freeze" />
        klaim A
      </text>
    </g>
    <g>
      <rect x="216" y="28" width="60" height="14" rx="7" fill="#34d399" opacity="0.25">
        <animate attributeName="x" from="216" to="180" dur="1.2s" begin="0.6s" fill="freeze" />
      </rect>
      <text fontSize="7" fill="currentColor" opacity="0.9" y="37" x="246" textAnchor="middle">
        <animate attributeName="x" from="246" to="210" dur="1.2s" begin="0.6s" fill="freeze" />
        klaim B
      </text>
    </g>
    {/* petir kontradiksi */}
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.4s" begin="1.9s" fill="freeze" />
      <path d="M170 20 L163 36 L171 36 L162 54" fill="none" stroke={C.gap} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round">
        <animate attributeName="stroke-opacity" values="1;0.35;1" dur="1.2s" begin="2s" repeatCount="indefinite" />
      </path>
      <text x="170" y="70" textAnchor="middle" fontSize="8" fontWeight="bold" fill={C.gap}>BERTENTANGAN</text>
      <text x="170" y="81" textAnchor="middle" fontSize="7" fill="currentColor" opacity="0.7">dicek model NLI (bukan tebakan)</text>
    </g>
    <text x="170" y="108" textAnchor="middle" fontSize="9" fill="currentColor" opacity="0.75">
      + pemeriksaan fragmentasi &amp; kelengkapan → {nGaps} calon gap
    </text>
  </svg>
)

// ── 4. Saringan 9 aturan logika ────────────────────────────────────
export const VisualRules = ({ passed = 1, flagged = 2, rejected = 0 }) => (
  <svg viewBox="0 0 340 130" className="w-full max-w-md" role="img"
    aria-label="Calon gap disaring 9 aturan logika">
    {/* calon gap jatuh dari atas */}
    {[0, 1, 2].map(i => (
      <circle key={i} cx={140 + i * 30} cy="14" r="8" fill={C.gap} opacity="0.8">
        <animate attributeName="cy" from="14" to="40" dur="0.9s" begin={`${i * 0.3}s`} fill="freeze" />
      </circle>
    ))}
    <text x="90" y="20" textAnchor="end" fontSize="8" fill="currentColor" opacity="0.7">calon gap</text>
    {/* corong saringan */}
    <path d="M110 48 L230 48 L196 78 L144 78 Z" fill={C.rule} opacity="0.12" stroke={C.rule} strokeWidth="1.5" />
    <text x="170" y="66" textAnchor="middle" fontSize="9" fontWeight="bold" fill={C.rule}>9 ATURAN LOGIKA</text>
    <text x="252" y="60" fontSize="7" fill="currentColor" opacity="0.65">kelayakan · sebab-akibat</text>
    <text x="252" y="70" fontSize="7" fill="currentColor" opacity="0.65">· konsistensi (tanpa AI)</text>
    {/* hasil keluar bawah */}
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="1.6s" fill="freeze" />
      <circle cx="120" cy="102" r="8" fill={C.rule} />
      <text x="120" y="122" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.8">{passed} lolos</text>
    </g>
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="1.9s" fill="freeze" />
      <circle cx="170" cy="102" r="8" fill={C.gap} />
      <text x="170" y="122" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.8">{flagged} ditinjau</text>
    </g>
    <g opacity="0">
      <animate attributeName="opacity" from="0" to="1" dur="0.5s" begin="2.2s" fill="freeze" />
      <circle cx="220" cy="102" r="8" fill={C.reject} opacity={rejected > 0 ? 1 : 0.25} />
      <text x="220" y="122" textAnchor="middle" fontSize="8" fill="currentColor" opacity="0.8">{rejected} dibuang</text>
    </g>
  </svg>
)

// ── 5. Skor evaluasi diri ──────────────────────────────────────────
export const VisualScore = ({ score = 0.8 }) => {
  const pct = Math.max(0, Math.min(1, Number(score) || 0))
  const dash = 251.2 * pct // keliling r=40
  return (
    <svg viewBox="0 0 340 110" className="w-full max-w-md" role="img"
      aria-label={`Skor evaluasi diri ${score}`}>
      <circle cx="90" cy="55" r="40" fill="none" stroke="currentColor" strokeWidth="8" opacity="0.1" />
      <circle cx="90" cy="55" r="40" fill="none" stroke={C.rule} strokeWidth="8"
        strokeLinecap="round" strokeDasharray={`${dash} 251.2`} transform="rotate(-90 90 55)">
        <animate attributeName="stroke-dasharray" from="0 251.2" to={`${dash} 251.2`} dur="1.4s" fill="freeze" />
      </circle>
      <text x="90" y="60" textAnchor="middle" fontSize="16" fontWeight="bold" fill="currentColor">{pct.toFixed(2)}</text>
      <text x="150" y="42" fontSize="9" fill="currentColor" opacity="0.85">Sistem menilai hasil kerjanya sendiri</text>
      <text x="150" y="56" fontSize="8" fill="currentColor" opacity="0.65">bukti cukup? konsisten? menjawab gap?</text>
      <text x="150" y="74" fontSize="8" fill={C.rule} fontWeight="bold">≥ ambang → layak ditampilkan</text>
      <text x="150" y="86" fontSize="7" fill="currentColor" opacity="0.6">(di bawah ambang → analisis diulang otomatis)</text>
    </svg>
  )
}

const StepVisual = ({ kind, ...props }) => {
  const visuals = {
    ingest: VisualIngest,
    facts: VisualFacts,
    compare: VisualCompare,
    rules: VisualRules,
    score: VisualScore,
  }
  const V = visuals[kind]
  if (!V) return null
  return (
    <div className="flex justify-center rounded-lg border bg-card/60 p-2 text-foreground">
      <V {...props} />
    </div>
  )
}

export default StepVisual
