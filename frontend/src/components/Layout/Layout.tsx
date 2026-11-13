import { MagnifyingGlass, User as UserIcon } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { searchTarget } from '@/lib/searchTarget'
import { useAuth } from '@/features/auth/AuthContext'
import styles from './Layout.module.css'

function SearchForm() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  function submit(e: FormEvent) {
    e.preventDefault()
    navigate(searchTarget(q))
  }
  return (
    <form className={styles.search} role="search" onSubmit={submit}>
      <label htmlFor="header-search" className={styles.srOnly}>
        Rechercher un appareil
      </label>
      <input
        id="header-search"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="iPhone 13, PC portable, Samsung…"
        className={styles.searchInput}
      />
      <button type="submit" className={styles.searchButton} aria-label="Lancer la recherche">
        <MagnifyingGlass size={20} />
      </button>
    </form>
  )
}

export function Layout() {
  const { user } = useAuth()
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.bar}>
          <Link to="/" className={styles.logo} aria-label="TechKoin, accueil">
            <img src="/brand/logo.svg" alt="" height={28} />
          </Link>
          <div className={styles.searchWrap}>
            <SearchForm />
          </div>
          <nav className={styles.nav} aria-label="Principal">
            <NavLink to="/vendre" className={styles.sell}>
              Vendre
            </NavLink>
            {user ? (
              <NavLink to="/compte" className={styles.account}>
                <UserIcon size={20} aria-hidden />
                <span className={styles.accountLabel}>{user.first_name}</span>
              </NavLink>
            ) : (
              <NavLink to="/connexion" className={styles.account}>
                <UserIcon size={20} aria-hidden />
                <span className={styles.accountLabel}>Connexion</span>
              </NavLink>
            )}
          </nav>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <p>TechKoin · Appareils neufs et d'occasion au Bénin.</p>
          <nav aria-label="Pied de page" className={styles.footerNav}>
            <Link to="/securite">Conseils de sécurité</Link>
            <Link to="/appareil-vole">Déclarer un appareil volé</Link>
            <Link to="/recherche">Toutes les annonces</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
