import { useState, useCallback, useRef, useEffect } from 'react'

const useApi = (apiFunction) => {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFunction(...args)
      if (mountedRef.current) setData(result)
      return result
    } catch (err) {
      if (err.name === 'CanceledError' || err.name === 'AbortError') throw err
      const message = err.userMessage || err.message || 'An error occurred'
      if (mountedRef.current) setError(message)
      throw err
    } finally {
      if (mountedRef.current) setLoading(false)
    }
  }, [apiFunction])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { data, loading, error, execute, reset }
}

export default useApi
