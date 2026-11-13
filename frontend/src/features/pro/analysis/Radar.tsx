import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import { formatFCFA, formatNumber } from '@/lib/format'
import { Change, LoadState, PeriodPicker, PreviewNotice } from '../shared'
import type { Demand, DemandRow } from '../types'
import styles from '../Pro.module.css'

function describe(row: DemandRow): string {
  const budget = row.budget_label ? ` ${row.budget_label}` : ''
  const city = row.city ? ` à ${row.city}` : ''
  return `${row.label}${budget}${city}`
}

/** P1: what buyers search for, set against what is on sale (spec 10.3). */
export default function Radar() {
  const [period, setPeriod] = useState<7 | 30>(7)
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['insights', 'demand', period],
    queryFn: () => api<Demand>('insights/demand/', { query: { period } }),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />

  return (
    <section className={styles.page} aria-labelledby="radar-title">
      <div className={styles.toolbar}>
        <div>
          <h2 id="radar-title" className={styles.h2}>
            Radar de la demande
          </h2>
          <p className={styles.hint}>
            Recherches des acheteurs comparées aux annonces en ligne. Un segment n’apparaît qu’à
            partir de {data.min_searches} recherches.
          </p>
        </div>
        <PeriodPicker value={period} options={[7, 30] as const} onChange={setPeriod} />
      </div>

      {data.recommendations && (
        <section className={styles.card} aria-labelledby="reco-title">
          <h3 id="reco-title" className={styles.h2}>
            À acheter en priorité
          </h3>
          <ol>
            {data.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ol>
          <p className={styles.note}>
            {data.used_ai
              ? 'Rédigé par l’IA à partir du tableau ci-dessous.'
              : 'Rédigé à partir du tableau ci-dessous.'}
          </p>
        </section>
      )}

      {data.rows.length === 0 ? (
        <EmptyState
          title="Pas encore assez de recherches"
          text={`Aucun segment n’atteint ${data.min_searches} recherches sur cette période.`}
        />
      ) : (
        <ul className={styles.rows}>
          {data.rows.map((r) => (
            <li key={`${r.label}-${r.budget_max}-${r.city}`} className={styles.row}>
              <div className={styles.rowMain}>
                <span className={styles.rowTitle}>{describe(r)}</span>
                <span className={styles.note}>
                  {r.supply <= 3 ? <Tag tone="red">Offre faible</Tag> : null}{' '}
                  {r.median_budget_fcfa ? `Budget médian ${formatFCFA(r.median_budget_fcfa)}` : ''}
                </span>
              </div>
              <dl className={styles.figures}>
                <div>
                  <dt>Recherches</dt>
                  <dd>{formatNumber(r.searches)}</dd>
                </div>
                <div>
                  <dt>Sans résultat</dt>
                  <dd>{formatNumber(r.no_result)}</dd>
                </div>
                <div>
                  <dt>Annonces en ligne</dt>
                  <dd>
                    {formatNumber(r.supply)}
                    {r.my_supply > 0 ? ` (dont ${r.my_supply} chez vous)` : ''}
                  </dd>
                </div>
                <div>
                  <dt>Évolution</dt>
                  <dd>
                    <Change value={r.change_pct} />
                    {r.change_pct === null ? 'nouveau' : ''}
                  </dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      )}
      <PreviewNotice meta={data} what="segment de demande" />
    </section>
  )
}
