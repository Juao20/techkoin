import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Suspense, lazy } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from '@/components/Layout/Layout'
import { ToastProvider } from '@/components/Toast/Toast'
import { AuthProvider } from '@/features/auth/AuthContext'
import { CompareProvider } from '@/features/compare/CompareContext'
import { Home } from './Home'

const Styleguide = import.meta.env.DEV
  ? lazy(() => import('../features/styleguide/Styleguide'))
  : null

const LoginPage = lazy(() => import('../features/auth/LoginPage'))
const RegisterPage = lazy(() => import('../features/auth/RegisterPage'))

const SearchPage = lazy(() => import('../features/search/SearchPage'))

const ListingPage = lazy(() => import('../features/listing/ListingPage'))

const PublishPage = lazy(() => import('../features/publish/PublishPage'))

const ShopPage = lazy(() => import('../features/shop/ShopPage'))
const AccountPage = lazy(() => import('../features/account/AccountPage'))
const SafetyPage = lazy(() => import('../features/pages/SafetyPage'))

const StolenReportPage = lazy(() => import('../features/trust/StolenReportPage'))

const ComparePage = lazy(() => import('../features/compare/ComparePage'))

const OrderPage = lazy(() => import('../features/orders/OrderPage'))

const ProLayout = lazy(() => import('../features/pro/ProLayout'))
const ProOverview = lazy(() => import('../features/pro/Overview'))
const ProListings = lazy(() => import('../features/pro/ListingsTab'))
const ProAnalysis = lazy(() => import('../features/pro/AnalysisTab'))
const ProOrders = lazy(() => import('../features/pro/OrdersTab'))
const ProSubscription = lazy(() => import('../features/pro/SubscriptionTab'))
const ProSettings = lazy(() => import('../features/pro/SettingsTab'))

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <CompareProvider>
            <BrowserRouter>
              <Suspense fallback={null}>
                <Routes>
                  {Styleguide && <Route path="/_styleguide" element={<Styleguide />} />}
                  <Route element={<Layout />}>
                    <Route path="/" element={<Home />} />
                    <Route path="/recherche" element={<SearchPage />} />
                    <Route path="/annonce/:slug" element={<ListingPage />} />
                    <Route path="/vendre" element={<PublishPage />} />
                    <Route path="/vendre/:id" element={<PublishPage />} />
                    <Route path="/boutique/:slug" element={<ShopPage />} />
                    <Route path="/compte" element={<AccountPage />} />
                    <Route path="/securite" element={<SafetyPage />} />
                    <Route path="/comparer" element={<ComparePage />} />
                    <Route path="/commande/:id" element={<OrderPage />} />
                    <Route path="/pro" element={<ProLayout />}>
                      <Route index element={<ProOverview />} />
                      <Route path="annonces" element={<ProListings />} />
                      <Route path="analyse" element={<ProAnalysis />} />
                      <Route path="commandes" element={<ProOrders />} />
                      <Route path="abonnement" element={<ProSubscription />} />
                      <Route path="parametres" element={<ProSettings />} />
                    </Route>
                    <Route path="/appareil-vole" element={<StolenReportPage />} />
                    <Route path="/connexion" element={<LoginPage />} />
                    <Route path="/inscription" element={<RegisterPage />} />
                  </Route>
                </Routes>
              </Suspense>
            </BrowserRouter>
          </CompareProvider>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}
