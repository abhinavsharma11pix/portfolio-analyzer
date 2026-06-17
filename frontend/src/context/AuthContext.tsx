import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { tokenStore, authService } from '../services/auth'
import type { User } from '../services/auth'

interface AuthCtx {
  user: User | null; isLoading: boolean; isLoggedIn: boolean
  login:    (email: string, password: string) => Promise<void>
  register: (email: string, username: string, password: string) => Promise<void>
  logout:   () => Promise<void>
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,      setUser]      = useState<User | null>(tokenStore.getUser())
  const [isLoading, setIsLoading] = useState(!!tokenStore.getAccess())

  useEffect(() => {
    if (!tokenStore.getAccess()) { setIsLoading(false); return }
    authService.me()
      .then(r => { setUser(r.data) })
      .catch(() => { tokenStore.clear(); setUser(null) })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authService.login(email, password)
    tokenStore.set(res.data); setUser(res.data.user ?? null)
  }, [])

  const register = useCallback(async (email: string, username: string, password: string) => {
    const res = await authService.register(email, username, password)
    tokenStore.set(res.data); setUser(res.data.user ?? null)
  }, [])

  const logout = useCallback(async () => {
    const rt = tokenStore.getRefresh()
    if (rt) { try { await authService.logout(rt) } catch { /* silent */ } }
    tokenStore.clear(); setUser(null)
  }, [])

  return (
    <Ctx.Provider value={{ user, isLoading, isLoggedIn: !!user, login, register, logout }}>
      {children}
    </Ctx.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}