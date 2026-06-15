import { Info } from 'lucide-react'

/**
 * Info banner that explains what a page/menu shows and what results appear there.
 * Matches the tab description banner style used on the Analysis Results page.
 */
const PageHelp = ({ icon: Icon = Info, title, description, items = [], className = '' }) => {
  return (
    <div className={`flex items-start gap-3 px-4 py-3 rounded-lg bg-blue-500/5 border border-blue-500/20 ${className}`}>
      <Icon className="w-5 h-5 mt-0.5 text-blue-500 flex-shrink-0" />
      <div className="min-w-0">
        {title && <p className="text-sm font-medium text-foreground mb-0.5">{title}</p>}
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
        {items.length > 0 && (
          <ul className="mt-1.5 space-y-0.5">
            {items.map((item, idx) => (
              <li key={idx} className="text-xs text-muted-foreground flex items-start gap-1.5">
                <span className="text-blue-500 mt-0.5">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default PageHelp
