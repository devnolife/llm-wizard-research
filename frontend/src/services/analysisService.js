import api from './api'

export const analysisService = {
  // Upload and analyze PDFs
  async uploadAndAnalyze(files, onUploadProgress) {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))

    const response = await api.post('/api/upload-and-analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress,
      timeout: 300000, // 5 minutes — large PDFs + busy server
    })
    return response.data
  },

  // Get analysis status
  async getAnalysisStatus(jobId, lang = 'en') {
    const response = await api.get(`/api/analysis-status/${jobId}`, {
      params: { lang }
    })
    return response.data
  },

  // Get recommendations
  async getRecommendations(query, options = {}) {
    const response = await api.post('/api/recommend', {
      query,
      max_results: options.max_results || 10,
      strategy: options.strategy || 'hybrid',
      user_context: options.user_context,
    })
    return response.data
  },

  // Detect research gaps
  async detectGaps(topic, depth = 'standard') {
    const response = await api.post('/api/gaps', {
      topic,
      depth,
    })
    return response.data
  },

  // Chat with research assistant
  async chat(message, conversationId = null, useHistory = true) {
    const response = await api.post('/api/chat', {
      message,
      use_history: useHistory,
      conversation_id: conversationId,
    })
    return response.data
  },
}

export default analysisService
