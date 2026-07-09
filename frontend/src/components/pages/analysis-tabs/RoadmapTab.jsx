import { Zap, TrendingUp, Target, Clock, ArrowRight, Map } from 'lucide-react'

const RoadmapTab = ({ parsedRoadmap }) => {
  const phaseIcons = { zap: Zap, trending: TrendingUp, target: Target, clock: Clock }
  const phaseColors = [
    { bg: 'bg-blue-500/10', text: 'text-blue-600 dark:text-blue-400', line: 'bg-blue-500' },
    { bg: 'bg-purple-500/10', text: 'text-purple-600 dark:text-purple-400', line: 'bg-purple-500' },
    { bg: 'bg-emerald-500/10', text: 'text-emerald-600 dark:text-emerald-400', line: 'bg-emerald-500' },
  ]
  return (
    <div className="space-y-4">
      <div className="mb-2">
        <h3 className="text-lg font-semibold">Peta Jalan Penelitian</h3>
        <p className="text-sm text-muted-foreground">Rencana terstruktur untuk arah penelitian masa depan.</p>
      </div>
      <div className="relative">
        {parsedRoadmap.map((phase, phaseIdx) => {
          const Icon = phaseIcons[phase.icon] || Clock
          const colors = phaseColors[phaseIdx % phaseColors.length]
          return (
            <div key={phaseIdx} className="relative flex gap-6 pb-8 last:pb-0">
              {phaseIdx < parsedRoadmap.length - 1 && (
                <div className={`absolute left-5 top-10 bottom-0 w-0.5 ${colors.line} opacity-20`} />
              )}
              <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                <Icon className={`w-5 h-5 ${colors.text}`} />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold mb-3">{phase.label}</h4>
                <div className="space-y-2">
                  {phase.items.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-2 p-3 rounded-md bg-secondary/30">
                      <ArrowRight className="w-4 h-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <span className="text-sm text-muted-foreground">{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      {parsedRoadmap.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Map className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">Belum ada peta jalan.</p>
        </div>
      )}
    </div>
  )
}

export default RoadmapTab
