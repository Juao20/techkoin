import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

const KEY = 'techkoin.compare'
export const MAX_COMPARE = 3

type CompareState = {
  ids: number[]
  has: (id: number) => boolean
  toggle: (id: number) => boolean
  clear: () => void
}

const CompareContext = createContext<CompareState | null>(null)

function readStored(): number[] {
  try {
    const raw = sessionStorage.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((n): n is number => typeof n === 'number').slice(0, MAX_COMPARE)
      : []
  } catch {
    return []
  }
}

function store(ids: number[]) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(ids))
  } catch {
    /* The selection still works without storage. */
  }
}

export function CompareProvider({ children }: { children: ReactNode }) {
  const [ids, setIds] = useState<number[]>(readStored)

  const toggle = useCallback(
    (id: number) => {
      if (ids.includes(id)) {
        const next = ids.filter((x) => x !== id)
        setIds(next)
        store(next)
        return true
      }
      if (ids.length >= MAX_COMPARE) return false
      const next = [...ids, id]
      setIds(next)
      store(next)
      return true
    },
    [ids],
  )

  const value = useMemo<CompareState>(
    () => ({
      ids,
      has: (id) => ids.includes(id),
      toggle,
      clear: () => {
        setIds([])
        store([])
      },
    }),
    [ids, toggle],
  )
  return <CompareContext.Provider value={value}>{children}</CompareContext.Provider>
}

export function useCompare(): CompareState {
  const ctx = useContext(CompareContext)
  if (!ctx) throw new Error('useCompare doit être utilisé dans CompareProvider')
  return ctx
}
