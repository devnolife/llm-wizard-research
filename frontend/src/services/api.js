import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes for long analysis requests
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      error.userMessage = 'Request timed out. Please try again.'
    } else if (!error.response) {
      error.userMessage = 'Network error. Please check your connection.'
    } else {
      const status = error.response.status
      const detail = error.response.data?.detail

      switch (status) {
        case 400:
          error.userMessage = detail || 'Invalid request. Please check your input.'
          break
        case 404:
          error.userMessage = detail || 'Resource not found.'
          break
        case 413:
          error.userMessage = 'File too large. Maximum size is 50MB.'
          break
        case 422:
          error.userMessage = detail || 'Invalid data format.'
          break
        case 429:
          error.userMessage = 'Too many requests. Please wait a moment.'
          break
        case 500:
          error.userMessage = detail || 'Server error. Please try again later.'
          break
        case 503:
          error.userMessage = 'Service unavailable. The server might be starting up.'
          break
        default:
          error.userMessage = detail || `Error (${status}). Please try again.`
      }
    }
    return Promise.reject(error)
  }
)

export default api
