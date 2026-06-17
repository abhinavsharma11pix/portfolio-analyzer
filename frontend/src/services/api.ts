/**
 * services/api.ts — Complete file.
 * Single axios instance, all requests go through API_BASE.
 * Attaches JWT access token automatically. Auto-refreshes on 401.
 */

import axios from 'axios'
import type {
  AxiosInstance,
  InternalAxiosRequestConfig,
} from 'axios'

import { API_BASE } from '../config/api'

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

// ── Attach access token to every outgoing request ──────────────
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('pa_access_token')

    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  }
)

// ── Auto-refresh access token on 401 ───────────────────────────
let isRefreshing = false
let pendingQueue: Array<() => void> = []

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry
    ) {
      original._retry = true

      const refreshToken =
        localStorage.getItem('pa_refresh_token')

      if (!refreshToken) {
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingQueue.push(() =>
            resolve(apiClient(original))
          )
        })
      }

      isRefreshing = true

      try {
        const res = await axios.post(
          `${API_BASE}/api/auth/refresh`,
          {
            refresh_token: refreshToken,
          }
        )

        localStorage.setItem(
          'pa_access_token',
          res.data.access_token
        )

        if (res.data.refresh_token) {
          localStorage.setItem(
            'pa_refresh_token',
            res.data.refresh_token
          )
        }

        pendingQueue.forEach((cb) => cb())
        pendingQueue = []

        return apiClient(original)
      } catch (refreshError) {
        localStorage.removeItem('pa_access_token')
        localStorage.removeItem('pa_refresh_token')

        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ── Portfolio API ──────────────────────────────────────────────
export const portfolioApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)

    return apiClient.post(
      '/api/portfolio/upload',
      form,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )
  },

  getRisk: (holdings: any[]) =>
    apiClient.post('/api/analytics/risk', {
      holdings,
    }),

  getAdvanced: (
    holdings: any[],
    riskMetrics: any
  ) =>
    apiClient.post(
      '/api/analytics/advanced',
      {
        holdings,
        risk_metrics: riskMetrics,
      }
    ),

  predict: (
    symbol: string,
    horizonDays = 30
  ) =>
    apiClient.get(
      `/api/portfolio/predict/${symbol}`,
      {
        params: {
          horizon_days: horizonDays,
        },
      }
    ),

  simulate: (payload: any) =>
    apiClient.post(
      '/api/analytics/simulate',
      payload
    ),

  savePortfolio: (
    name: string,
    holdings: any[],
    summary: any
  ) =>
    apiClient.post('/api/portfolios', {
      name,
      holdings,
      summary,
    }),

  listPortfolios: () =>
    apiClient.get('/api/portfolios'),

  deletePortfolio: (id: number) =>
    apiClient.delete(`/api/portfolios/${id}`),
}

export default apiClient