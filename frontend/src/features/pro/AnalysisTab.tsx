import { lazy, Suspense } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthContext'
import { ProOnly } from './shared'
import styles from './Pro.module.css'

const Radar = lazy(() => import('./analysis/Radar'))
const Pricing = lazy(() => import('./analysis/Pricing'))
const Dormant = lazy(() => import('./analysis/Dormant'))
const Reports = lazy(() => import('./analysis/Reports'))
const Chat = lazy(() => import('./analysis/Chat'))
const Bulk = lazy(() => import('./analysis/Bulk'))
const Competition = lazy(() => import('./analysis/Competition'))

const MODULES = [
  { id: 'radar', label: 'Demande', pro: false, view: Radar },
  { id: 'prix', label: 'Prix', pro: false, view: Pricing },
  { id: 'dormant', label: 'Stock dormant', pro: false, view: Dormant },
  { id: 'rapport', label: 'Rapport', pro: true, view: Reports },
  { id: 'chat', label: 'Discuter', pro: true, view: Chat },
  { id: 'optimisation', label: 'Optimisation', pro: true, view: Bulk },
  { id: 'concurrence', label: 'Concurrence', pro: true, view: Competition },
] as const

const LOCKED: Record<string, { title: string; text: string }> = {
  rapport: {
    title: 'Rapport hebdomadaire',
    text: 'Chaque lundi à 8 h : vues, contacts, ventes, meilleurs produits et 3 actions prioritaires, dans l’interface et par e-mail.',
  },
  chat: {
    title: 'Discuter avec vos chiffres',
    text: 'Posez vos questions en français (« Combien de contacts sur les iPhone ce mois ? ») et obtenez la réponse calculée sur votre boutique.',
  },
  optimisation: {
    title: 'Optimisation en lot',
    text: 'De nouveaux titres et descriptions pour jusqu’à 50 annonces, à valider annonce par annonce.',
  },
  concurrence: {
    title: 'Comparer à la concurrence',
    text: 'Les 3 annonces concurrentes les plus proches des vôtres, et ce qui peut convaincre un acheteur de les préférer.',
  },
}

/** Tab « Analyse » (P1 to P7). Free shops see a real preview of P1 to P3 and a description of the rest. */
export default function AnalysisTab() {
  const { user } = useAuth()
  const pro = user?.shop?.plan === 'pro'
  const [params, setParams] = useSearchParams()
  const current = MODULES.find((m) => m.id === params.get('module')) ?? MODULES[0]
  const View = current.view

  return (
    <>
      <nav className={styles.nav} aria-label="Modules d’analyse">
        {MODULES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={styles.navLink}
            aria-current={m.id === current.id ? 'page' : undefined}
            onClick={() => setParams({ module: m.id }, { replace: true })}
          >
            {m.label}
          </button>
        ))}
      </nav>
      {current.pro && !pro ? (
        <ProOnly {...(LOCKED[current.id] as { title: string; text: string })} />
      ) : (
        <Suspense fallback={<p>Chargement…</p>}>
          <View />
        </Suspense>
      )}
    </>
  )
}
