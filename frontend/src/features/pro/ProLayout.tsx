import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { useAuth } from '@/features/auth/AuthContext'
import styles from './Pro.module.css'

const SECTIONS = [
  { to: '/pro', label: 'Vue d’ensemble', end: true },
  { to: '/pro/annonces', label: 'Annonces' },
  { to: '/pro/analyse', label: 'Analyse' },
  { to: '/pro/commandes', label: 'Commandes' },
  { to: '/pro/abonnement', label: 'Abonnement' },
  { to: '/pro/parametres', label: 'Paramètres' },
]

/** Frame of /pro/*: signed-in shop accounts only. The plan shown is the server's answer. */
export default function ProLayout() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <p>Chargement…</p>
  if (!user) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />
  if (!user.shop) {
    return (
      <EmptyState
        title="Espace réservé aux boutiques"
        text="Ce compte est un compte particulier. Créez un compte boutique pour accéder au tableau de bord."
        action={<Link to="/inscription">Créer un compte boutique</Link>}
      />
    )
  }
  const pro = user.shop.plan === 'pro'
  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>{user.shop.name}</h1>
          <p className={styles.meta}>
            <Tag tone={pro ? 'green' : 'neutral'}>{pro ? 'Offre Pro' : 'Offre gratuite'}</Tag>
            <Link to={`/boutique/${user.shop.slug}`}>Voir ma vitrine</Link>
          </p>
        </div>
        <Link to="/vendre" className={styles.offerLink}>
          Vendre un appareil
        </Link>
      </header>
      <nav className={styles.nav} aria-label="Tableau de bord">
        {SECTIONS.map((s) => (
          <NavLink key={s.to} to={s.to} end={s.end} className={styles.navLink}>
            {s.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
