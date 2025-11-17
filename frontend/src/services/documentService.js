import api from './api'

export const documentService = {
  // Upload and ingest a single PDF
  async uploadDocument(file, metadata = {}) {
    const formData = new FormData()
    formData.append('file', file)

    if (metadata.title) formData.append('title', metadata.title)
    if (metadata.authors) formData.append('authors', metadata.authors)
    if (metadata.year) formData.append('year', metadata.year)

    const response = await api.post('/api/ingest', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  // Search documents
  async search(query, filters = {}) {
    const response = await api.post('/api/search', {
      query,
      top_k: filters.top_k || 10,
      filters: filters.metadata || null,
    })
    return response.data
  },

  // Get statistics
  async getStats() {
    const response = await api.get('/api/stats')
    return response.data
  },

  // Delete document
  async deleteDocument(docId) {
    const response = await api.delete(`/api/documents/${docId}`)
    return response.data
  },
}

export default documentService
