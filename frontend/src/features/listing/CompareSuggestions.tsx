import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import type { ListingCardApi, ListingDetailApi } from '@/lib/types'
import styles from './CompareSuggestions.module.css'

/** Two alternatives chosen by the server (same category, close price and usage scores). */
export function CompareSuggestions({ listing }: { listing: ListingDetailApi }) {
  const { data } = useQuery({
    queryKey: ['compare-suggestions', listing.id],
    queryFn: () =>
      api<ListingCardApi[]>('ai/compare/suggestions/', { query: { listing_id: listing.id } }),
  })
  if (!data || data.length === 0) return null
  const ids = [listing.id, ...data.map((d) => d.id)]
  return (
    <section className={styles.wrap} aria-labelledby="compare-similar">
      <h2 id="compare-similar" className={styles.title}>
        Comparer avec des annonces similaires
      </h2>
      <ul className={styles.list}>
        {data.map((d) => (
          <li key={d.id}>
            <Link to={`/annonce/${d.slug}`}>{d.title}</Link>
            <span className={styles.price}>{formatFCFA(d.price_fcfa)}</span>
          </li>
        ))}
      </ul>
      <Link className={styles.go} to={`/comparer?ids=${ids.join(',')}`}>
        Voir le verdict TechKoin
      </Link>
    </section>
  )
}
