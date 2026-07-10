import { Suspense } from 'react'
import LoadingSpinner from './LoadingSpinner'

const LazyBoundary = ({ children, message = 'Memuat halaman...' }) => (
  <Suspense fallback={<LoadingSpinner message={message} />}>
    {children}
  </Suspense>
)

export default LazyBoundary
