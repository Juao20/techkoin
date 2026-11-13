import { Link } from 'react-router-dom'
import { formatFCFA } from '@/lib/format'
import { GradeMark, type Grade } from '../GradeMark/GradeMark'
import { Tag } from '../Tag/Tag'
import styles from './ListingCard.module.css'

export type ListingCardData = {
  id: string
  href: string
  title: string
  specs: string
  priceFcfa: number
  priceBadge?: 'good_deal' | 'fair' | 'above_market'
  city: string
  age: string
  grade?: Grade
  imageUrl?: string
  keyboard?: string
  verifiedSeller?: boolean
}

const BADGES = {
  good_deal: { tone: 'yellow', label: 'Bonne affaire' },
  fair: { tone: 'green', label: 'Prix correct' },
  above_market: { tone: 'red', label: 'Au-dessus du marché' },
} as const

type Props = {
  listing: ListingCardData
  compared?: boolean
  onCompareChange?: (checked: boolean) => void
  /** The first cards of a page are what the visitor sees first: load them at once. */
  priority?: boolean
}

export function ListingCard({ listing, compared = false, onCompareChange, priority }: Props) {
  const badge = listing.priceBadge ? BADGES[listing.priceBadge] : null
  return (
    <article className={styles.card}>
      <div className={styles.photo}>
        {listing.imageUrl && (
          <img
            src={listing.imageUrl}
            alt={listing.title}
            loading={priority ? 'eager' : 'lazy'}
            fetchPriority={priority ? 'high' : 'auto'}
            width={480}
            height={360}
          />
        )}
      </div>
      <div className={styles.body}>
        <h3 className={styles.title}>
          <Link to={listing.href} className={styles.link}>
            {listing.title}
          </Link>
        </h3>
        <p className={styles.specs}>{listing.specs}</p>
        <p className={styles.price}>{formatFCFA(listing.priceFcfa)}</p>
        <div className={styles.tags}>
          {badge && <Tag tone={badge.tone}>{badge.label}</Tag>}
          {listing.keyboard && <Tag>{listing.keyboard}</Tag>}
          {listing.verifiedSeller && <Tag tone="green">Boutique vérifiée</Tag>}
        </div>
        <p className={styles.meta}>
          {listing.city} · {listing.age}
        </p>
        {listing.grade && <GradeMark grade={listing.grade} />}
      </div>
      {onCompareChange && (
        <label className={styles.compare}>
          <input
            type="checkbox"
            checked={compared}
            onChange={(e) => onCompareChange(e.target.checked)}
          />
          Comparer
        </label>
      )}
    </article>
  )
}
