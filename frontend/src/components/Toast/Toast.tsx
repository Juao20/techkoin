import * as RadixToast from '@radix-ui/react-toast'
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import styles from './Toast.module.css'

type ToastItem = { id: number; message: string }
type Ctx = { notify: (message: string) => void }

const ToastContext = createContext<Ctx | null>(null)

export function useToast(): Ctx {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const notify = useCallback((message: string) => {
    setItems((prev) => [...prev, { id: Date.now() + Math.random(), message }])
  }, [])
  return (
    <ToastContext.Provider value={{ notify }}>
      <RadixToast.Provider duration={5000} swipeDirection="left">
        {children}
        {items.map((t) => (
          <RadixToast.Root
            key={t.id}
            className={styles.toast}
            onOpenChange={(open) => {
              if (!open) setItems((prev) => prev.filter((x) => x.id !== t.id))
            }}
          >
            <RadixToast.Description>{t.message}</RadixToast.Description>
          </RadixToast.Root>
        ))}
        <RadixToast.Viewport className={styles.viewport} label="Notifications" />
      </RadixToast.Provider>
    </ToastContext.Provider>
  )
}
