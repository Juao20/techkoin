import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
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
      <BrowserRouter>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/" element={<Home />} />
            {Styleguide && <Route path="/_styleguide" element={<Styleguide />} />}
          </Routes>
        </Suspense>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
