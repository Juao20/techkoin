import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react'
import { api } from '@/lib/api'
import type { User } from '@/lib/types'

type AuthState = {
  user: User | null
  loading: boolean
  login: (identifier: string, password: string) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => Promise<void>
}

export type RegisterPayload = {
  email: string
  phone: string
  password: string
  first_name: string
  last_name?: string
  account_type: 'particulier' | 'boutique'
  city?: string
  shop_name?: string
}

const AuthContext = createContext<AuthState | null>(null)
const ME_KEY = ['me']

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const { data, isPending } = useQuery({
    queryKey: ME_KEY,
    queryFn: () => api<{ user: User | null }>('auth/me/'),
    staleTime: 5 * 60 * 1000,
  })

  const setUser = useCallback(
    (user: User | null) => queryClient.setQueryData(ME_KEY, { user }),
    [queryClient],
  )

  const value = useMemo<AuthState>(
    () => ({
      user: data?.user ?? null,
      loading: isPending,
      async login(identifier, password) {
        const user = await api<User>('auth/login/', {
          method: 'POST',
          body: { identifier, password },
        })
        setUser(user)
        return user
      },
      async register(payload) {
        const user = await api<User>('auth/register/', { method: 'POST', body: payload })
        setUser(user)
        return user
      },
      async logout() {
        await api('auth/logout/', { method: 'POST' })
        setUser(null)
        queryClient.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
      },
    }),
    [data, isPending, setUser, queryClient],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé dans AuthProvider')
  return ctx
}
