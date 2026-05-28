import axios from 'axios'

const BASE = 'http://localhost:8000'

export interface User {
  id: number; email: string; username: string
  created_at: string; last_login: string | null
}

export interface Tokens {
  access_token: string; refresh_token: string
  token_type: string; user: User
}

const K = { access: 'pa_at', refresh: 'pa_rt', user: 'pa_u' }

export const tokenStore = {
  set:        (t: Tokens) => {
    localStorage.setItem(K.access, t.access_token)
    localStorage.setItem(K.refresh, t.refresh_token)
    localStorage.setItem(K.user, JSON.stringify(t.user))
  },
  getAccess:  () => localStorage.getItem(K.access),
  getRefresh: () => localStorage.getItem(K.refresh),
  getUser:    (): User | null => {
    const r = localStorage.getItem(K.user)
    return r ? JSON.parse(r) : null
  },
  clear: () => Object.values(K).forEach(k => localStorage.removeItem(k)),
}

export const authApi = axios.create({ baseURL: BASE })

authApi.interceptors.request.use(cfg => {
  const t = tokenStore.getAccess()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

let refreshing: Promise<string | null> | null = null

authApi.interceptors.response.use(r => r, async err => {
  const orig = err.config
  if (err.response?.status === 401 && !orig._retry) {
    orig._retry = true
    if (!refreshing) {
      refreshing = (async () => {
        const rt = tokenStore.getRefresh()
        if (!rt) return null
        try {
          const res = await axios.post(`${BASE}/api/auth/refresh`, { refresh_token: rt })
          tokenStore.set(res.data)
          return res.data.access_token
        } catch {
          tokenStore.clear()
          window.location.href = '/login'
          return null
        } finally { refreshing = null }
      })()
    }
    const token = await refreshing
    if (token) {
      orig.headers.Authorization = `Bearer ${token}`
      return authApi(orig)
    }
  }
  return Promise.reject(err)
})

export const authService = {
  register: (email: string, username: string, password: string) =>
    axios.post<Tokens>(`${BASE}/api/auth/register`, { email, username, password }),
  login: (email: string, password: string) =>
    axios.post<Tokens>(`${BASE}/api/auth/login`, { email, password }),
  logout: (refresh_token: string) =>
    authApi.post('/api/auth/logout', { refresh_token }),
  me: () => authApi.get<User>('/api/auth/me'),
}

export const portfolioService = {
  list:         ()                                        => authApi.get('/api/portfolios'),
  create:       (name: string, description?: string)     => authApi.post('/api/portfolios', { name, description }),
  get:          (id: number)                             => authApi.get(`/api/portfolios/${id}`),
  update:       (id: number, name: string, desc?: string)=> authApi.put(`/api/portfolios/${id}`, { name, description: desc }),
  delete:       (id: number)                             => authApi.delete(`/api/portfolios/${id}`),
  saveHoldings: (id: number, holdings: any[], summary: any) =>
    authApi.post(`/api/portfolios/${id}/holdings`, { holdings, summary }),
  getHistory:   (id: number, days = 90)                  => authApi.get(`/api/portfolios/${id}/history`, { params: { days } }),
}

export const fundamentalsService = {
  get:     (symbol: string) => authApi.get(`/api/fundamentals/${symbol}`),
  summary: (symbol: string) => authApi.get(`/api/fundamentals/${symbol}/summary`),
  batch:   (symbols: string[]) => authApi.post('/api/fundamentals/batch', { symbols }),
}