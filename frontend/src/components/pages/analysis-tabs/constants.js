import { Target, BarChart3, Tag, Search, Lightbulb, Map, Share2, Zap } from 'lucide-react'

export const TABS = [
  { id: 'proposal', label: 'Usulan', icon: Target, desc: 'Indikator usulan penelitian hasil sintesis jurnal Anda, berbasis indikator synthesis gap (Cooper, 1998): gap yang terdeteksi, arah penelitian yang diusulkan, dan alurnya. Bersifat alat bantu keputusan — perlu divalidasi peneliti.' },
  { id: 'overview', label: 'Ringkasan', icon: BarChart3, desc: 'Gambaran umum hasil analisis: jumlah topik, gap, dan rekomendasi yang ditemukan dari paper Anda. Mulai dari sini.' },
  { id: 'topics', label: 'Topik & Analisis', icon: Tag, desc: 'Topik-topik utama yang dibahas dalam paper Anda, hasil ekstraksi otomatis oleh AI dari isi dokumen.' },
  { id: 'gaps', label: 'Gap Penelitian', icon: Search, desc: 'Indikator synthesis gap (Cooper/Booth): fragmentasi (topik terpecah tak terintegrasi), inkonsistensi (temuan bertentangan), atau ketidaklengkapan kolektif. Indikatif — perlu ditinjau peneliti.' },
  { id: 'recommendations', label: 'Rekomendasi', icon: Lightbulb, desc: 'Saran arah penelitian yang bisa Anda ambil berdasarkan gap yang ditemukan, lengkap dengan alasan (WHY) dan cara memulainya (HOW).' },
  { id: 'roadmap', label: 'Peta Jalan', icon: Map, desc: 'Rencana penelitian bertahap: apa yang bisa dikerjakan dalam jangka pendek, menengah, dan panjang.' },
  { id: 'knowledge-graph', label: 'Graf Pengetahuan', icon: Share2, desc: 'Peta visual hubungan antar konsep (metode, domain, temuan) yang diekstrak dari paper. Titik = konsep, garis = hubungan antar konsep.' },
  { id: 'pipeline', label: 'Pipeline', icon: Zap, advanced: true, desc: 'Detail teknis proses analisis di belakang layar: berapa fakta yang diekstrak, hasil validasi aturan, dan skor kepercayaan. Untuk verifikasi kualitas hasil.' },
]

export const GAP_TYPES = ['FRAGMENTATION', 'INCONSISTENCY', 'INCOMPLETENESS']

export const GAP_COLORS = {
  FRAGMENTATION: { border: 'border-blue-500', bg: 'bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400', label: 'Fragmentasi', desc: 'Paper membahas topik yang sama dari sudut berbeda tanpa integrasi' },
  INCONSISTENCY: { border: 'border-amber-500', bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: 'Inkonsistensi', desc: 'Temuan yang bertentangan antar paper' },
  INCOMPLETENESS: { border: 'border-red-500', bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'Ketidaklengkapan', desc: 'Aspek kritis yang belum tercakup dalam literatur' },
}

// Penjelasan "cara menemukan" tiap jenis gap — untuk transparansi metode deteksi
export const GAP_METHOD = {
  FRAGMENTATION: {
    look: 'Mencari jurnal yang membahas fenomena sama tetapi dari sudut/teori berbeda dan tidak saling mengaitkan temuannya.',
    how: 'Sistem mengelompokkan topik antar-paper lalu memeriksa keterhubungannya di Knowledge Graph. Bila antar-kelompok nyaris tidak ada keterkaitan, itu tanda fragmentasi.',
  },
  INCONSISTENCY: {
    look: 'Mencari temuan atau klaim yang saling bertentangan antar paper tanpa ada yang merekonsiliasi.',
    how: 'Sistem membandingkan klaim (fakta Subjek–Predikat–Objek) antar paper dan mengecek kontradiksi. Bila ada dua klaim berlawanan tentang hal yang sama, itu tanda inkonsistensi.',
  },
  INCOMPLETENESS: {
    look: 'Mencari aspek penting dari fenomena yang belum tercakup secara kolektif oleh kumpulan paper.',
    how: 'Sistem memetakan cakupan aspek/konsep di Knowledge Graph lalu mengidentifikasi aspek yang jarang atau tidak pernah muncul. Aspek yang kosong itulah celah ketidaklengkapan.',
  },
}

export const PRIORITY_COLORS = {
  high: { bg: 'bg-red-500/10', text: 'text-red-600 dark:text-red-400', label: 'Prioritas Tinggi' },
  medium: { bg: 'bg-amber-500/10', text: 'text-amber-600 dark:text-amber-400', label: 'Prioritas Sedang' },
  low: { bg: 'bg-green-500/10', text: 'text-green-600 dark:text-green-400', label: 'Prioritas Rendah' },
}

export const LOADING_STEPS = [
  { label: 'Memproses PDF', threshold: 10 },
  { label: 'Mengekstrak Topik', threshold: 40 },
  { label: 'Menganalisis Penelitian', threshold: 60 },
  { label: 'Mendeteksi Gap', threshold: 75 },
  { label: 'Menghasilkan Insight', threshold: 90 },
]
