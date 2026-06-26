import { useNavigate } from 'react-router-dom'
import { Home } from 'lucide-react'

const NotFoundPage = () => {
  const navigate = useNavigate()

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-6">
      <div className="text-center reveal">
        <p className="font-display text-[7rem] leading-none font-extrabold text-gradient mb-2">404</p>
        <h2 className="text-xl font-semibold mb-2">Halaman tidak ditemukan</h2>
        <p className="text-muted-foreground mb-7 max-w-sm mx-auto">
          Halaman yang Anda cari tidak ada atau telah dipindahkan.
        </p>
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold shadow-glow transition-all duration-200 hover:bg-primary/90 active:scale-[0.99]"
        >
          <Home className="w-4 h-4" />
          Kembali ke Beranda
        </button>
      </div>
    </div>
  )
}

export default NotFoundPage
