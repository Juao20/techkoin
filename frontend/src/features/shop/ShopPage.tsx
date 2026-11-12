import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import { toCard } from '@/lib/listings'
import type { ListingCardApi, Page } from '@/lib/types'
import styles from './ShopPage.module.css'

type ShopPublic = {
  name: string
  slug: string
  logo: string | null
  description: string
  address: string
  city: string
  quartier: string
  opening_hours: Record<string, string>
  verified: boolean
  member_since: string
  active_listings: number
  sold_count: number
}

const DAYS: Record<string, string> = {
  mon: 'Lundi',
  tue: 'Mardi',
  wed: 'Mercredi',
  thu: 'Jeudi',
  fri: 'Vendredi',
  sat: 'Samedi',
  sun: 'Dimanche',
}

export default function ShopPage() {
  const { slug = '' } = useParams()
  const [params, setParams] = useSearchParams()
  const page = Math.max(1, Number(params.get('page')) || 1)

  const shop = useQuery({
    queryKey: ['shop', slug],
    queryFn: () => api<ShopPublic>(`shops/${slug}/`),
  })
  const listings = useQuery({
    queryKey: ['shop', slug, 'listings', page],
    queryFn: () => api<Page<ListingCardApi>>(`shops/${slug}/listings/`, { query: { page } }),
    enabled: shop.isSuccess,
  })

  if (shop.isPending) return <p>Chargement de la boutique…</p>
  if (shop.isError) {
    return (
      <EmptyState
        title="Boutique introuvable"
        text="Cette boutique n’existe pas ou a été fermée."
        action={<Link to="/recherche">Voir les annonces</Link>}
      />
    )
  }
  const s = shop.data
  const hours = Object.entries(s.opening_hours ?? {}).filter(([k]) => DAYS[k])
  const totalPages = listings.data ? Math.max(1, Math.ceil(listings.data.count / 24)) : 1

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        {s.logo ? (
          <img className={styles.logo} src={s.logo} alt="" width={72} height={72} />
        ) : (
          <span className={styles.logo} aria-hidden>
            {s.name.slice(0, 1).toUpperCase()}
          </span>
        )}
        <div>
          <h1 className={styles.title}>{s.name}</h1>
          <p className={styles.meta}>
            {s.city}
            {s.quartier ? `, ${s.quartier}` : ''} · membre depuis{' '}
            {new Date(s.member_since).getFullYear()}
          </p>
          <div className={styles.tags}>
            {s.verified && <Tag tone="green">Boutique vérifiée</Tag>}
            <Tag>{s.active_listings} annonces en ligne</Tag>
            {s.sold_count > 0 && <Tag>{s.sold_count} ventes</Tag>}
          </div>
        </div>
      </header>

      {(s.description || s.address || hours.length > 0) && (
        <section className={styles.about}>
          {s.description && <p>{s.description}</p>}
          {s.address && (
            <p>
              <strong>Adresse :</strong> {s.address}
            </p>
          )}
          {hours.length > 0 && (
            <dl className={styles.hours}>
              {hours.map(([k, v]) => (
                <div key={k}>
                  <dt>{DAYS[k]}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      <section aria-label="Annonces de la boutique">
        <h2 className={styles.h2}>Annonces</h2>
        {listings.isPending ? (
          <p>Chargement…</p>
        ) : listings.data && listings.data.results.length > 0 ? (
          <>
            <ul className={styles.grid}>
              {listings.data.results.map((l) => (
                <li key={l.id}>
                  <ListingCard listing={toCard(l)} />
                </li>
              ))}
            </ul>
            {totalPages > 1 && (
              <nav className={styles.pager} aria-label="Pagination">
                <Button
                  variant="secondary"
                  disabled={page <= 1}
                  onClick={() => setParams({ page: String(page - 1) })}
                >
                  Précédent
                </Button>
                <span>
                  Page {page} sur {totalPages}
                </span>
                <Button
                  variant="secondary"
                  disabled={page >= totalPages}
                  onClick={() => setParams({ page: String(page + 1) })}
                >
                  Suivant
                </Button>
              </nav>
            )}
          </>
        ) : (
          <EmptyState
            title="Aucune annonce en ligne"
            text="Cette boutique n’a rien publié pour le moment."
          />
        )}
      </section>
    </div>
  )
}
