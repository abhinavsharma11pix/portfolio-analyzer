import axios from 'axios'
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const BASE = 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE,
  timeout: 90_000,
})

// All API calls — single source of truth
export const portfolioApi = {
  upload: (formData: FormData) =>
    api.post('/api/portfolio/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  getRisk: (holdings: any[]) =>
    api.post('/api/portfolio/risk', { holdings }),

  getInsights: (holdings: any[], riskMetrics: any, summary: any) =>
    api.post('/api/portfolio/insights', { holdings, risk_metrics: riskMetrics, summary }),

  getDecisions: (holdings: any[], riskMetrics: any, advancedMetrics: any, summary: any) =>
    api.post('/api/portfolio/decisions', {
      holdings,
      risk_metrics:     riskMetrics,
      advanced_metrics: advancedMetrics ?? {},
      predictions:      {},
      summary:          summary ?? {},
    }),

  getAdvanced: (holdings: any[], riskMetrics: any) =>
    api.post('/api/analytics/advanced', { holdings, risk_metrics: riskMetrics }),

  getBenchmark: (holdings: any[]) =>
    api.post('/api/analytics/benchmark', { holdings }),

  simulate: (holdings: any[]) =>
    api.post('/api/analytics/simulate', { holdings }),

  predict: (symbol: string) =>
    api.get(`/api/portfolio/predict/${symbol}`),

  marketStatus: () =>
    api.get('/api/market/status'),
}

  export const recommendationApi = {
    getGoals: () =>
      api.get('/api/recommendation/goals'),

    getProfile: (data: {
      amount: number; goal: string; horizon: string
      market: string; preferred_sectors?: string[]
    }) => api.post('/api/recommendation/profile', data),

    generate: (data: {
      amount: number; goal: string; horizon: string; market: string
      exchange?: string; preferred_sectors?: string[]
    }) => api.post('/api/recommendation/generate', data),
}