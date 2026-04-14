import { Loader } from 'lucide-react'

const LoadingSpinner = ({ message = 'Loading...', size = 'lg' }) => {
  const sizes = {
    sm: { icon: 'w-4 h-4', text: 'text-xs' },
    md: { icon: 'w-6 h-6', text: 'text-sm' },
    lg: { icon: 'w-8 h-8', text: 'text-sm' },
  }
  const s = sizes[size] || sizes.lg

  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <Loader className={`${s.icon} animate-spin text-muted-foreground`} />
      {message && <p className={`${s.text} text-muted-foreground`}>{message}</p>}
    </div>
  )
}

export default LoadingSpinner
