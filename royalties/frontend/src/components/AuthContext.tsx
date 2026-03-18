/** Authentication context — stores token and user state. */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { UserResponse } from '@/types'
import { getMe } from '@/api'

interface AuthState {
  user: UserResponse | null
  token: string | null
  loading: boolean
  setAuth: (token: string, user: UserResponse) => void
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('rsv_token'))
  const [loading, setLoading] = useState(!!localStorage.getItem('rsv_token'))

  const logout = useCallback(() => {
    localStorage.removeItem('rsv_token')
    localStorage.removeItem('rsv_nickname')
    setToken(null)
    setUser(null)
  }, [])

  const setAuth = useCallback((newToken: string, newUser: UserResponse) => {
    localStorage.setItem('rsv_token', newToken)
    localStorage.setItem('rsv_nickname', newUser.nickname)
    setToken(newToken)
    setUser(newUser)
  }, [])

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => logout())
      .finally(() => setLoading(false))
  }, [token, logout])

  return (
    <AuthContext.Provider value={{ user, token, loading, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
