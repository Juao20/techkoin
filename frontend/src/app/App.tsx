import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout/Layout'
import { ToastProvider } from '@/components/Toast/Toast'
import { AuthProvider } from '@/features/auth/AuthContext'
import { Home } from './Home'

const Styleguide = import.meta.env.DEV
  ? lazy(() => import('../features/styleguide/Styleguide'))
  : null

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Suspense fallback={null}>
              <Routes>
                {Styleguide && <Route path="/_styleguide" element={<Styleguide />} />}
                <Route element={<Layout />}>
                  <Route path="/" element={<Home />} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}
