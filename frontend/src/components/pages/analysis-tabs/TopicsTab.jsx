import { BookOpen } from 'lucide-react'
import Markdown from '../../common/Markdown'

const TopicsTab = ({ data }) => (
  <div className="space-y-4">
    <div className="mb-2">
      <h3 className="text-lg font-semibold">Topik Penelitian yang Diekstrak</h3>
      <p className="text-sm text-muted-foreground">Topik yang teridentifikasi dari analisis perbandingan antar-paper yang Anda unggah.</p>
    </div>
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {(data?.topics || []).map((topic, idx) => (
        <div key={idx} className="rounded-lg border bg-card p-5 hover:border-primary/30 transition-colors">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 text-sm font-bold">
              {idx + 1}
            </div>
            <h4 className="font-medium text-sm leading-snug">{topic.replace(/^\d+[.)]\s*/, '')}</h4>
          </div>
        </div>
      ))}
    </div>
    {data?.summary && (
      <div className="rounded-lg border bg-card p-6 mt-6">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-5 h-5 text-primary" />
          <h3 className="font-semibold">Ringkasan Analisis Komparatif</h3>
        </div>
        <Markdown content={data.summary} />
      </div>
    )}
  </div>
)

export default TopicsTab
