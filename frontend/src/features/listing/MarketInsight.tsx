import { PriceRange } from '@/components/PriceRange/PriceRange'
import { ScoreBar } from '@/components/ScoreBar/ScoreBar'
import { Tag } from '@/components/Tag/Tag'
import type { ListingDetailApi } from '@/lib/types'
import { USAGE_LABELS } from '@/lib/usage'
import styles from './MarketInsight.module.css'

/** Estimate range and usage scores. Both are computed by the server, never by the interface. */
export function MarketInsight({ listing: l }: { listing: ListingDetailApi }) {
  const hasEstimate = l.estimate_low !== null && l.estimate_high !== null
  const scores = Object.entries(l.usage_scores ?? {})
  if (!hasEstimate && scores.length === 0) return null

  return (
    <section className={styles.wrap} aria-labelledby="insight">
      <h2 id="insight" className={styles.title}>
        Prix et usages
      </h2>
      {hasEstimate && (
        <div className={styles.block}>
          <PriceRange low={l.estimate_low!} high={l.estimate_high!} price={l.price_fcfa} />
          <p className={styles.note}>
            {l.estimate_indicative
              ? 'Estimation indicative : il y a peu d’annonces comparables, elle part du prix neuf.'
              : 'Estimation calculée à partir des annonces et ventes récentes du même modèle.'}
          </p>
        </div>
      )}
      {scores.length > 0 && (
        <div className={styles.block}>
          {l.advised_usage && (
            <p className={styles.advised}>
              Usage conseillé : <Tag tone="green">{USAGE_LABELS[l.advised_usage]}</Tag>
            </p>
          )}
          {scores.map(([key, score]) => (
            <ScoreBar key={key} label={USAGE_LABELS[key] ?? key} score={score} />
          ))}
        </div>
      )}
    </section>
  )
}
