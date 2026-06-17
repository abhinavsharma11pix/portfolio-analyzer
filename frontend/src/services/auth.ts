/**
 * services/auth.ts
 * Uses apiClient from services/api.ts
 */

import { apiClient } from './api'

export interface User {
  id: number
  email: string
  username: string
  created_at?: string
  last_login?: string | null
}

export interface Tokens {
  access_token: string
  refresh_token: string
  token_type: string
  user?: User
}

const K = {
  access: 'pa_access_token',
  refresh: 'pa_refresh_token',
  user: 'pa_user',
}

export const tokenStore = {
  set: (t: Tokens) => {
    localStorage.setItem(K.access, t.access_token)
    localStorage.setItem(K.refresh, t.refresh_token)

    if (t.user) {
      localStorage.setItem(K.user, JSON.stringify(t.user))
    }
  },

  getAccess: () => localStorage.getItem(K.access),

  getRefresh: () => localStorage.getItem(K.refresh),

  getUser: (): User | null => {
    const raw = localStorage.getItem(K.user)

    if (!raw) return null

    try {
      return JSON.parse(raw)
    } catch {
      return null
    }
  },

  clear: () => {
    Object.values(K).forEach((k) => localStorage.removeItem(k))
  },
}

export const authService = {
  register: async (
    email: string,
    username: string,
    password: string
  ) => {
    const res = await apiClient.post<Tokens>(
      '/api/auth/register',
      {
        email,
        username,
        password,
      }
    )

    tokenStore.set(res.data)

    return res
  },

  login: async (
    email: string,
    password: string
  ) => {
    const res = await apiClient.post<Tokens>(
      '/api/auth/login',
      {
        email,
        password,
      }
    )

    tokenStore.set(res.data)

    return res
  },

  logout: async (
    refresh_token: string
  ) => {
    return apiClient.post(
      '/api/auth/logout',
      { refresh_token }
    )
  },

  me: async () => {
    return apiClient.get<User>(
      '/api/auth/me'
    )
  },
}

export const portfolioService = {
  list: () =>
    apiClient.get('/api/portfolios'),

  create: (
    name: string,
    description?: string
  ) =>
    apiClient.post('/api/portfolios', {
      name,
      description,
    }),

  get: (id: number) =>
    apiClient.get(`/api/portfolios/${id}`),

  update: (
    id: number,
    name: string,
    description?: string
  ) =>
    apiClient.put(`/api/portfolios/${id}`, {
      name,
      description,
    }),

  delete: (id: number) =>
    apiClient.delete(`/api/portfolios/${id}`),

  saveHoldings: (
    id: number,
    holdings: any[],
    summary: any
  ) =>
    apiClient.post(
      `/api/portfolios/${id}/holdings`,
      {
        holdings,
        summary,
      }
    ),

  getHistory: (
    id: number,
    days = 90
  ) =>
    apiClient.get(
      `/api/portfolios/${id}/history`,
      {
        params: { days },
      }
    ),
}

export const fundamentalsService = {
  get: (symbol: string) =>
    apiClient.get(
      `/api/fundamentals/${symbol}`
    ),

  summary: (symbol: string) =>
    apiClient.get(
      `/api/fundamentals/${symbol}/summary`
    ),

  batch: (symbols: string[]) =>
    apiClient.post(
      '/api/fundamentals/batch',
      { symbols }
    ),
}

export default authService