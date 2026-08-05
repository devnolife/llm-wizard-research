import { useEffect, useRef } from 'react'
import { Loader, CheckCircle2, Circle } from 'lucide-react'

// Log proses bergaya notebook Jupyter: setiap aktivitas = satu "cell"
// dengan status running/done dan timestamp.
// Memperlihatkan seluruh langkah pipeline secara eksplisit.
const NotebookProcessLog = ({ activities = [], running = true }) => {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [activities.length])

  if (!activities.length) return null

  return (
    <div className="mt-6 rounded-xl border bg-card overflow-hidden text-left">
      <div className="flex items-center justify-between border-b bg-secondary/50 px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Log Proses — langkah demi langkah
        </p>
        <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          {running ? (
            <><span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> berjalan</>
          ) : (
            <><span className="h-2 w-2 rounded-full bg-muted-foreground/50" /> selesai</>
          )}
        </span>
      </div>
      <div className="max-h-72 overflow-y-auto p-3 text-[13px] leading-relaxed">
        {activities.map((activity, index) => {
          const isLast = index === activities.length - 1
          const isRunning = isLast && running
          return (
            <div
              key={`${activity.time}-${index}`}
              className={`group flex items-start gap-0 rounded-md border-l-[3px] mb-1.5 ${isRunning
                ? 'border-l-emerald-500 bg-emerald-500/[0.06]'
                : activity.kind === 'phase'
                  ? 'border-l-primary/70 bg-primary/[0.04]'
                  : 'border-l-transparent hover:bg-secondary/40'
                }`}
            >
              {/* Nomor langkah */}
              <span className={`select-none shrink-0 grid h-6 w-6 mt-1 ml-1.5 place-items-center rounded-full text-[11px] font-bold ${isRunning
                ? 'bg-emerald-500 text-white'
                : 'bg-primary/10 text-primary'}`}>
                {index + 1}
              </span>
              <div className="flex min-w-0 flex-1 items-start justify-between gap-2 py-1.5 pl-2.5 pr-2.5">
                <span className={`min-w-0 break-words ${isRunning ? 'text-foreground font-medium' : 'text-foreground/85'}`}>
                  {activity.text}
                </span>
                <span className="flex shrink-0 items-center gap-1.5 pt-0.5 text-[10px] text-muted-foreground">
                  {activity.time}
                  {isRunning ? (
                    <Loader className="h-3 w-3 animate-spin text-emerald-500" />
                  ) : (
                    <CheckCircle2 className="h-3 w-3 text-emerald-500/80" />
                  )}
                </span>
              </div>
            </div>
          )
        })}
        {running && (
          <div className="flex items-center gap-2 px-2.5 py-1 text-[11px] text-muted-foreground">
            <Circle className="h-2 w-2 animate-pulse" /> menunggu langkah berikutnya…
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

export default NotebookProcessLog
