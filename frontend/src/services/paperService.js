import api from './api'

export const paperService = {
  // Search external papers
  async searchExternalPapers(query, options = {}) {
    const response = await api.post('/api/papers/search', {
      query,
      max_results: options.max_results || 10,
      sources: options.sources || ['arxiv', 'core', 'crossref'],
      deduplicate: options.deduplicate !== false,
      year_from: options.year_from,
      year_to: options.year_to,
      embedding_model: options.embedding_model || 'all-MiniLM-L6-v2',
    })
    return response.data
  },

  // Ingest external paper by ID
  async ingestExternalPaper(paperId, source = 'semantic_scholar') {
    const response = await api.post('/api/papers/ingest-external', null, {
      params: { paper_id: paperId, source },
    })
    return response.data
  },

  // Batch ingest papers
  async batchIngestPapers(query, options = {}) {
    const response = await api.post('/api/papers/batch-ingest', null, {
      params: {
        query,
        max_results: options.max_results || 20,
        sources: options.sources,
      },
    })
    return response.data
  },
}

export default paperService
