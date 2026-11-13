import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { api } from '@/lib/api'
import { formatFCFA, formatNumber } from '@/lib/format'
import { Change, LoadState, PERIODS, PeriodPicker } from './shared'
import type { Period, ShopStats } from './types'
import styles from './Pro.module.css'

/** Bars for views, a line for contacts. Plain SVG, no animation, no gradient. */
function Chart({ series }: { series: ShopStats['series'] }) {
  const width = 600
  const height = 160
  const max = Math.max(1, ...series.map((s) => s.views))
  const step = width / series.length
  const barWidth = Math.max(1, step - (series.length > 40 ? 0.5 : 2))
  const y = (v: number) => height - 4 - (v / max) * (height - 12)
  const line = series.map(
    (s, i) => `${(i * step + step / 2).toFixed(1)},${y(s.contacts).toFixed(1)}`,
  )
  const total = series.reduce((n, s) => n + s.views, 0)
  return (
    <svg
      className={styles.chart}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={`Vues et contacts par jour sur ${series.length} jours, ${formatNumber(total)} vues au total`}
    >
      {series.map((s, i) => (
        <rect
          key={s.date}
          x={i * step + (step - barWidth) / 2}
          y={y(s.views)}
          width={barWidth}
          height={height - 4 - y(s.views)}
          fill="var(--green)"
        />
      ))}
      <polyline points={line.join(' ')} fill="none" stroke="var(--ink)" strokeWidth="2" />
    </svg>
  )
}

export default function Overview() {
  const [period, setPeriod] = useState<Period>(30)
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['shop', 'stats', period],
    queryFn: () => api<ShopStats>('shop/stats/', { query: { period } }),
  })
  const state = <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  if (!data) return state
  const t = data.totals
  const kpis = [
    { label: 'Vues', value: formatNumber(t.views), change: t.change.views },
    { label: 'Contacts', value: formatNumber(t.contacts), change: t.change.contacts },
    { label: 'Favoris', value: formatNumber(t.favorites), change: t.change.favorites },
    {
      label: 'Taux de contact',
      value: `${String(t.contact_rate).replace('.', ',')} %`,
      change: null,
    },
    { label: 'Ventes', value: formatNumber(t.sales), change: t.change.sales },
  ]
  const best = data.listings.filter((l) => l.views > 0).slice(0, 5)

  return (
    <>
      <div className={styles.toolbar}>
        <h2 className={styles.h2}>Sur les {period} derniers jours</h2>
        <PeriodPicker value={period} options={PERIODS} onChange={setPeriod} />
      </div>

      <ul className={styles.kpis} aria-label="Chiffres clés">
        {kpis.map((k) => (
          <li key={k.label} className={styles.kpi}>
            <span className={styles.kpiLabel}>{k.label}</span>
            <span className={styles.kpiValue}>{k.value}</span>
            <span className={styles.kpiChange}>
              {k.change === null ? ' ' : <Change value={k.change} />}
              {k.change === null ? '' : ' sur la période précédente'}
            </span>
          </li>
        ))}
      </ul>
      {t.revenue_fcfa > 0 && (
        <p className={styles.hint}>
          Chiffre d’affaires des ventes conclues : {formatFCFA(t.revenue_fcfa)}.
        </p>
      )}

      <section className={styles.card} aria-labelledby="chart-title">
        <h2 id="chart-title" className={styles.h2}>
          Vues et contacts par jour
        </h2>
        <Chart series={data.series} />
        <ul className={styles.legend}>
          <li>
            <span className={styles.swatchViews} aria-hidden />
            Vues
          </li>
          <li>
            <span className={styles.swatchContacts} aria-hidden />
            Contacts
          </li>
        </ul>
      </section>

      <section aria-labelledby="best-title" className={styles.page}>
        <h2 id="best-title" className={styles.h2}>
          Annonces les plus vues
        </h2>
        {best.length === 0 ? (
          <EmptyState
            title="Pas encore de vues"
            text="Les vues et les contacts de vos annonces apparaîtront ici dès les premières visites."
            action={<Link to="/vendre">Publier une annonce</Link>}
          />
        ) : (
          <ul className={styles.rows}>
            {best.map((l) => (
              <li key={l.id} className={styles.row}>
                <div className={styles.rowMain}>
                  <span className={styles.rowTitle}>
                    <Link to={`/annonce/${l.slug}`}>{l.title}</Link>
                  </span>
                  <span className={styles.note}>{formatFCFA(l.price_fcfa)}</span>
                </div>
                <dl className={styles.figures}>
                  <div>
                    <dt>Vues</dt>
                    <dd>{formatNumber(l.views)}</dd>
                  </div>
                  <div>
                    <dt>Contacts</dt>
                    <dd>{formatNumber(l.contacts)}</dd>
                  </div>
                  <div>
                    <dt>Favoris</dt>
                    <dd>{formatNumber(l.favorites)}</dd>
                  </div>
                  <div>
                    <dt>Taux de contact</dt>
                    <dd>{String(l.contact_rate).replace('.', ',')} %</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
