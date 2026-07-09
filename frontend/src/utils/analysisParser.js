// Pure parsing helpers for analysis results (extracted from AnalysisResults.jsx)

// Parse numbered text block into structured items
export const parseNumberedList = (text) => {
  if (!text) return []
  if (Array.isArray(text)) return text
  const lines = text.split('\n').filter(l => l.trim())
  const items = []
  let current = ''
  for (const line of lines) {
    if (/^\d+[.)]\s/.test(line.trim())) {
      if (current) items.push(current.trim())
      current = line.trim().replace(/^\d+[.)]\s*/, '')
    } else if (line.trim().startsWith('-') || line.trim().startsWith('•')) {
      if (current) items.push(current.trim())
      current = line.trim().replace(/^[-•]\s*/, '')
    } else {
      current += ' ' + line.trim()
    }
  }
  if (current) items.push(current.trim())
  return items.length > 0 ? items : [text]
}

// Parse structured recommendation with title/why/how
export const parseStructuredRecommendation = (text) => {
  if (!text) return { title: '', description: text || '', why: '', how: '' }
  const titleMatch = text.match(/^(?:\[([^\]]+)\]:\s*)?(.+?)(?:\s*WHY:|$)/s)
  const whyMatch = text.match(/WHY:\s*(.+?)(?:\s*HOW:|$)/s)
  const howMatch = text.match(/HOW:\s*(.+)/s)

  if (whyMatch || howMatch) {
    return {
      title: (titleMatch?.[1] || '').trim(),
      description: (titleMatch?.[2] || text.split(/\s*WHY:/)[0] || '').trim(),
      why: (whyMatch?.[1] || '').trim(),
      how: (howMatch?.[1] || '').trim(),
    }
  }
  // Fallback: try splitting on colon for "Title: description" format
  const colonIdx = text.indexOf(':')
  if (colonIdx > 0 && colonIdx < 80) {
    return { title: text.slice(0, colonIdx).trim(), description: text.slice(colonIdx + 1).trim(), why: '', how: '' }
  }
  return { title: '', description: text, why: '', how: '' }
}

// Parse structured gap with title/description/type
export const parseStructuredGap = (text) => {
  if (!text) return { title: '', description: text || '', type: null }
  const titleMatch = text.match(/TITLE:\s*(.+?)(?:\n|DESCRIPTION:|$)/s)
  const descMatch = text.match(/DESCRIPTION:\s*(.+?)(?:\nTYPE:|$)/s)
  const typeMatch = text.match(/TYPE:\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS)/i)

  if (titleMatch || typeMatch) {
    return {
      title: (titleMatch?.[1] || '').trim(),
      description: (descMatch?.[1] || text).trim(),
      type: typeMatch?.[1]?.toUpperCase() || null,
    }
  }
  return { title: '', description: text, type: null }
}

// Parse roadmap plain-text into phases
export const parseRoadmap = (text) => {
  if (!text) return []
  const phases = []
  const sections = text.split(/(?=(?:short|medium|long|phase|tahap|jangka)\s*[-:]?\s*(?:term|pendek|menengah|panjang)?)/i)
  for (const section of sections) {
    if (!section.trim()) continue
    const lines = section.trim().split('\n').filter(l => l.trim())
    if (lines.length === 0) continue
    let label = 'Phase'
    let icon = 'clock'
    const firstLine = lines[0].toLowerCase()
    if (firstLine.includes('short') || firstLine.includes('pendek')) { label = 'Short Term'; icon = 'zap' }
    else if (firstLine.includes('medium') || firstLine.includes('menengah')) { label = 'Medium Term'; icon = 'trending' }
    else if (firstLine.includes('long') || firstLine.includes('panjang')) { label = 'Long Term'; icon = 'target' }
    const items = parseNumberedList(lines.slice(1).join('\n'))
    if (items.length > 0 && items[0] !== '') phases.push({ label, icon, items })
  }
  if (phases.length === 0) {
    const items = parseNumberedList(text)
    if (items.length > 1) {
      const third = Math.ceil(items.length / 3)
      phases.push({ label: 'Short Term', icon: 'zap', items: items.slice(0, third) })
      phases.push({ label: 'Medium Term', icon: 'trending', items: items.slice(third, third * 2) })
      phases.push({ label: 'Long Term', icon: 'target', items: items.slice(third * 2) })
    } else {
      phases.push({ label: 'Research Plan', icon: 'clock', items })
    }
  }
  return phases
}

// Ubah verdict rule-engine (PASS/FLAG/REJECT atau ACCEPT/REVIEW/REJECT) jadi label ramah
export const verdictLabel = (v) => {
  const key = String(v || '').toUpperCase()
  if (key === 'PASS' || key === 'ACCEPT') return 'Lolos'
  if (key === 'FLAG' || key === 'REVIEW') return 'Perlu Ditinjau'
  if (key === 'REJECT') return 'Ditolak'
  return v || ''
}

// ── Higher-level normalizers (bodies of former useMemo hooks) ──

// Defensive: older jobs may carry a record whose fields are raw JSON text
// (a parser bug). Recover the real fields so nothing ugly reaches the UI.
const recoverRawJson = (rec) => {
  const probe = String(rec.description || rec.title || '')
  if (!probe.trim().startsWith('{')) return rec
  const m = probe.match(/\{[\s\S]*\}/)
  if (!m) return rec
  try {
    const obj = JSON.parse(m[0])
    if (obj && typeof obj === 'object') {
      return {
        ...rec,
        title: obj.title || rec.title,
        description: obj.description || '',
        gap_type: obj.gap_type || obj.type || rec.gap_type,
        why: obj.why || rec.why,
        how: obj.how || rec.how,
      }
    }
  } catch { /* leave as-is */ }
  return rec
}

export const parseRecommendations = (recs) => {
  recs = recs || []
  if (Array.isArray(recs)) {
    return recs.map((rec, idx) => {
      if (typeof rec === 'object' && rec !== null) {
        const r = recoverRawJson(rec)
        return {
          title: r.title || '',
          description: r.description || '',
          gap_type: (r.gap_type || r.type || '').toUpperCase() || null,
          why: r.why || '',
          how: r.how || '',
          priority: r.priority || (idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low'),
          index: idx,
        }
      }
      // Legacy string format fallback
      return { ...parseStructuredRecommendation(String(rec)), priority: idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low', index: idx }
    })
  }
  // Legacy: plain text
  const raw = parseNumberedList(recs)
  return raw.map((text, idx) => ({
    ...parseStructuredRecommendation(text),
    priority: idx < 2 ? 'high' : idx < 4 ? 'medium' : 'low',
    index: idx,
  }))
}

export const parseGaps = (gaps) => {
  return (gaps || []).map((gap, idx) => {
    if (typeof gap === 'object' && gap !== null) {
      return {
        title: gap.title || `Gap ${idx + 1}`,
        description: gap.description || '',
        type: (gap.type || '').toUpperCase() || null,
        confidence: gap.confidence,
        rule_engine_verdict: gap.rule_engine_verdict,
        evidence: gap.evidence || [],
        suggested_directions: gap.suggested_directions || [],
        index: idx,
        raw: gap,
      }
    }
    // Legacy string format fallback
    return { ...parseStructuredGap(String(gap)), index: idx, raw: gap }
  })
}

export const parseRoadmapData = (roadmap) => {
  // Bersihkan sisa markdown (**), penomoran, dan bullet dari tiap item
  const cleanItem = (s) => String(s)
    .replace(/\*\*/g, '')
    .replace(/^\s*[-•*]\s*/, '')
    .replace(/^\s*\d+[.)]\s*/, '')
    .trim()
  const pickIcon = (name, idx) => {
    const n = (name || '').toLowerCase()
    if (n.includes('short') || n.includes('pendek')) return 'zap'
    if (n.includes('medium') || n.includes('menengah')) return 'trending'
    if (n.includes('long') || n.includes('panjang')) return 'target'
    return ['zap', 'trending', 'target', 'clock'][idx] || 'clock'
  }
  if (Array.isArray(roadmap)) {
    return roadmap.map((phase, idx) => {
      if (typeof phase === 'object' && phase !== null) {
        const label = phase.phase || `Tahap ${idx + 1}`
        const items = (phase.items || []).map(cleanItem).filter(Boolean)
        return { label, icon: pickIcon(label, idx), items }
      }
      return { label: `Tahap ${idx + 1}`, icon: pickIcon('', idx), items: [cleanItem(phase)].filter(Boolean) }
    })
  }
  // Legacy: plain text
  return parseRoadmap(roadmap)
}
