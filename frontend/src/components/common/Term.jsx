import { useId } from 'react'

// Penjelasan singkat & ramah untuk istilah teknis yang muncul di seluruh aplikasi.
// Dipakai oleh komponen <Term> untuk menampilkan tooltip glosarium.
export const GLOSSARY = {
  KG: 'Knowledge Graph — jaringan konsep (metode, domain, temuan) beserta hubungannya yang diekstrak dari paper.',
  'Knowledge Graph': 'Jaringan konsep (metode, domain, temuan) beserta hubungannya yang diekstrak dari paper.',
  SPO: 'Subject–Predicate–Object — bentuk fakta terstruktur, mis. (CNN) – (digunakan untuk) – (klasifikasi citra).',
  RAG: 'Retrieval-Augmented Generation — AI mengambil potongan paper relevan lebih dulu, lalu menyusun jawaban yang bersumber.',
  'Rule Engine': 'Validator logika (simbolik) yang menilai indikator gap: Lolos, Perlu Ditinjau, atau Ditolak.',
  'Neuro-Simbolik': 'Gabungan kekuatan neural (LLM) dan simbolik (aturan logika) untuk menghasilkan sekaligus memvalidasi temuan.',
  'synthesis gap': 'Kondisi di mana literatur tentang suatu fenomena belum menghasilkan kesimpulan terpadu — karena fragmentasi, inkonsistensi, atau ketidaklengkapan kolektif (Cooper, 1998; Booth dkk., 2012).',
  confidence: 'Skor keyakinan sistem terhadap suatu indikator gap (0–100%).',
  keyakinan: 'Skor keyakinan sistem terhadap suatu indikator gap (0–100%).',
}

/**
 * Membungkus sebuah istilah agar menampilkan penjelasan singkat saat di-hover/fokus.
 * Pemakaian: <Term k="KG">KG</Term> atau <Term def="penjelasan kustom">istilah</Term>.
 * Jika tidak ada definisi yang cocok, teks ditampilkan apa adanya (tanpa tooltip).
 */
const Term = ({ children, k, def, className = '' }) => {
  const key = k || (typeof children === 'string' ? children : '')
  const definition = def || GLOSSARY[key]
  const tooltipId = useId()

  if (!definition) return <>{children}</>

  return (
    <span className="relative inline-flex group align-baseline">
      <span
        tabIndex={0}
        aria-describedby={tooltipId}
        className={`underline decoration-dotted decoration-muted-foreground/60 underline-offset-2 cursor-help outline-none rounded-sm focus-visible:ring-2 focus-visible:ring-primary/40 ${className}`}
      >
        {children}
      </span>
      <span
        id={tooltipId}
        role="tooltip"
        className="pointer-events-none absolute left-1/2 bottom-full z-50 mb-2 w-60 -translate-x-1/2 rounded-md border bg-background p-2.5 text-xs font-normal normal-case leading-relaxed text-muted-foreground shadow-lg opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {definition}
      </span>
    </span>
  )
}

export default Term
