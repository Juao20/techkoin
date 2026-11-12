import { formatFCFA } from '@/lib/format'
import styles from './PriceRange.module.css'

type Props = { low: number; high: number; price: number }

export function PriceRange({ low, high, price }: Props) {
  const spread = high - low
  const min = low - spread * 0.5
  const max = high + spread * 0.5
  const pct = (v: number) => Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))
  return (
    <div className={styles.wrap}>
      <div className={styles.track}>
        <span
          className={styles.range}
          style={{ left: `${pct(low)}%`, width: `${pct(high) - pct(low)}%` }}
        />
        <span className={styles.marker} style={{ left: `${pct(price)}%` }} aria-hidden="true" />
      </div>
      <p className={styles.caption}>
        Prix du marché : <span className={styles.mono}>{formatFCFA(low)}</span> –{' '}
        <span className={styles.mono}>{formatFCFA(high)}</span>
      </p>
    </div>
  )
}
