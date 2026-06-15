// Renderer Markdown ringan (tanpa dependensi eksternal).
// Mendukung: heading (#..######), **tebal**, *miring*, `kode`,
// daftar berpoin (-, *, •), daftar bernomor (1. / 1)), dan paragraf.

// Render format inline di dalam satu baris teks.
const renderInline = (text, keyPrefix) => {
  const nodes = []
  const regex = /(\*\*([^*]+)\*\*|`([^`]+)`|\*([^*\n]+)\*)/g
  let lastIndex = 0
  let match
  let i = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index))
    if (match[2] !== undefined) {
      nodes.push(<strong key={`${keyPrefix}-b${i}`} className="font-semibold text-foreground">{match[2]}</strong>)
    } else if (match[3] !== undefined) {
      nodes.push(<code key={`${keyPrefix}-c${i}`} className="px-1 py-0.5 rounded bg-secondary text-[0.85em] font-mono">{match[3]}</code>)
    } else if (match[4] !== undefined) {
      nodes.push(<em key={`${keyPrefix}-i${i}`}>{match[4]}</em>)
    }
    lastIndex = regex.lastIndex
    i++
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex))
  return nodes
}

const isHeading = (l) => /^#{1,6}\s+/.test(l.trim())
const isBullet = (l) => /^[-*•]\s+/.test(l.trim())
const isNumbered = (l) => /^\d+[.)]\s+/.test(l.trim())

const HEADING_CLASS = {
  1: 'text-lg font-bold text-foreground mt-4 mb-2',
  2: 'text-base font-bold text-foreground mt-4 mb-2',
  3: 'text-sm font-semibold text-foreground mt-3 mb-1.5',
  4: 'text-sm font-semibold text-foreground mt-3 mb-1.5',
  5: 'text-sm font-medium text-foreground mt-2 mb-1',
  6: 'text-sm font-medium text-foreground mt-2 mb-1',
}

const Markdown = ({ content, className = '' }) => {
  if (!content) return null
  const lines = String(content).split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const trimmed = lines[i].trim()
    if (!trimmed) { i++; continue }

    const heading = trimmed.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] })
      i++
      continue
    }

    if (isBullet(lines[i])) {
      const items = []
      while (i < lines.length && isBullet(lines[i])) {
        items.push(lines[i].trim().replace(/^[-*•]\s+/, ''))
        i++
      }
      blocks.push({ type: 'ul', items })
      continue
    }

    if (isNumbered(lines[i])) {
      const items = []
      while (i < lines.length && isNumbered(lines[i])) {
        items.push(lines[i].trim().replace(/^\d+[.)]\s+/, ''))
        i++
      }
      blocks.push({ type: 'ol', items })
      continue
    }

    const para = []
    while (
      i < lines.length && lines[i].trim() &&
      !isHeading(lines[i]) && !isBullet(lines[i]) && !isNumbered(lines[i])
    ) {
      para.push(lines[i].trim())
      i++
    }
    blocks.push({ type: 'p', text: para.join(' ') })
  }

  return (
    <div className={`text-sm leading-relaxed space-y-2 ${className || 'text-muted-foreground'}`}>
      {blocks.map((b, idx) => {
        if (b.type === 'heading') {
          const Tag = `h${Math.min(b.level + 2, 6)}`
          return <Tag key={idx} className={HEADING_CLASS[b.level]}>{renderInline(b.text, `h${idx}`)}</Tag>
        }
        if (b.type === 'ul') {
          return (
            <ul key={idx} className="list-disc pl-5 space-y-1">
              {b.items.map((it, j) => <li key={j}>{renderInline(it, `ul${idx}-${j}`)}</li>)}
            </ul>
          )
        }
        if (b.type === 'ol') {
          return (
            <ol key={idx} className="list-decimal pl-5 space-y-1">
              {b.items.map((it, j) => <li key={j}>{renderInline(it, `ol${idx}-${j}`)}</li>)}
            </ol>
          )
        }
        return <p key={idx}>{renderInline(b.text, `p${idx}`)}</p>
      })}
    </div>
  )
}

export default Markdown
