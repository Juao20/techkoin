import { useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { searchTarget } from '@/lib/searchTarget'
import { api } from '@/lib/api'
import { CATEGORY_LABELS, toCard } from '@/lib/listings'
import type { ListingCardApi, Page } from '@/lib/types'
import styles from './Home.module.css'

export function Home() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const latest = useQuery({
    queryKey: ['listings', 'home'],
    queryFn: () => api<Page<ListingCardApi>>('listings/', { query: { sort: 'recent' } }),
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    navigate(searchTarget(q))
  }

  return (
    <div className={styles.page}>
      <section className={styles.hero}>
        <h1 className={styles.title}>Appareils neufs et d’occasion, près de chez vous</h1>
        <p className={styles.lead}>
          Smartphones, tablettes et ordinateurs vendus par des boutiques et des particuliers au
          Bénin.
        </p>
        <form className={styles.search} role="search" onSubmit={submit}>
          <label htmlFor="home-search" className={styles.srOnly}>
            Rechercher un appareil
          </label>
          <input
            id="home-search"
            type="search"
            className={styles.input}
            placeholder="iPhone 13, PC portable HP, Samsung A54…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <button type="submit" className={styles.submit}>
            Rechercher
          </button>
        </form>
      </section>

      <section aria-labelledby="cats">
        <h2 id="cats" className={styles.h2}>
          Parcourir par catégorie
        </h2>
        <ul className={styles.cats}>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <li key={value}>
              <Link to={`/recherche?category=${value}`} className={styles.cat}>
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="latest">
        <div className={styles.sectionHead}>
          <h2 id="latest" className={styles.h2}>
            Dernières annonces
          </h2>
          <Link to="/recherche?sort=recent" className={styles.more}>
            Tout voir
          </Link>
        </div>
        {latest.isPending ? (
          <p>Chargement…</p>
        ) : latest.data && latest.data.results.length > 0 ? (
          <ul className={styles.grid}>
            {latest.data.results.slice(0, 8).map((l) => (
              <li key={l.id}>
                <ListingCard listing={toCard(l)} />
              </li>
            ))}
          </ul>
        ) : (
          <p className={styles.empty}>
            Aucune annonce pour le moment. <Link to="/vendre">Publiez la première.</Link>
          </p>
        )}
      </section>

      <section className={styles.steps} aria-labelledby="how">
        <h2 id="how" className={styles.h2}>
          Vendre en trois minutes
        </h2>
        <ol>
          <li>Choisissez votre modèle, tout se pré-remplit.</li>
          <li>Prenez les photos demandées avec votre téléphone.</li>
          <li>Fixez votre prix. Les acheteurs vous écrivent sur WhatsApp.</li>
        </ol>
        <Link to="/vendre" className={styles.cta}>
          Vendre un appareil
        </Link>
      </section>
    </div>
  )
}
