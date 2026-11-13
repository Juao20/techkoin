import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { useToast } from '@/components/Toast/Toast'
import { ApiError, api } from '@/lib/api'
import { formatFCFA, formatNumber } from '@/lib/format'
import { Change, LoadState, dateFr } from '../shared'
import type { Report, ReportSummary } from '../types'
import styles from '../Pro.module.css'

function Detail({ id }: { id: number }) {
  const { data } = useQuery({
    queryKey: ['insights', 'report', id],
    queryFn: () => api<Report>(`insights/reports/${id}/`),
  })
  if (!data) return <p>Chargement…</p>
  const f = data.figures
  return (
    <article className={styles.card} aria-label="Rapport">
      <h3 className={styles.h2}>
        Semaine du {dateFr.format(new Date(data.period_start))} au{' '}
        {dateFr.format(new Date(data.period_end))}
      </h3>
      <p>{data.summary}</p>
      <ul className={styles.kpis} aria-label="Chiffres de la semaine">
        <li className={styles.kpi}>
          <span className={styles.kpiLabel}>Vues</span>
          <span className={styles.kpiValue}>{formatNumber(f.views)}</span>
          <span className={styles.kpiChange}>
            <Change value={f.change.views} />
          </span>
        </li>
        <li className={styles.kpi}>
          <span className={styles.kpiLabel}>Contacts</span>
          <span className={styles.kpiValue}>{formatNumber(f.contacts)}</span>
          <span className={styles.kpiChange}>
            <Change value={f.change.contacts} />
          </span>
        </li>
        <li className={styles.kpi}>
          <span className={styles.kpiLabel}>Favoris</span>
          <span className={styles.kpiValue}>{formatNumber(f.favorites)}</span>
        </li>
        <li className={styles.kpi}>
          <span className={styles.kpiLabel}>Ventes</span>
          <span className={styles.kpiValue}>{formatNumber(f.sales)}</span>
          <span className={styles.kpiChange}>{formatFCFA(f.revenue_fcfa)}</span>
        </li>
      </ul>
      {f.best_listings.length > 0 && (
        <section>
          <h4 className={styles.h2}>Meilleurs produits</h4>
          <ol>
            {f.best_listings.map((b) => (
              <li key={b.title}>
                {b.title} : {b.views} vue(s), {b.contacts} contact(s)
              </li>
            ))}
          </ol>
        </section>
      )}
      <section>
        <h4 className={styles.h2}>Actions prioritaires</h4>
        <ol>
          {data.actions.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ol>
      </section>
      <p className={styles.note}>
        {data.used_ai
          ? 'Texte rédigé par l’IA à partir de chiffres calculés.'
          : 'Texte généré à partir de chiffres calculés.'}
        {data.emailed_at
          ? ` Envoyé par e-mail le ${dateFr.format(new Date(data.emailed_at))}.`
          : ''}
      </p>
    </article>
  )
}

/** P4: the weekly report, kept in the interface and e-mailed every Monday at 8:00. */
export default function Reports() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [chosen, setChosen] = useState<number | null>(null)
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['insights', 'reports'],
    queryFn: () => api<{ results: ReportSummary[] }>('insights/reports/'),
  })
  const generate = useMutation({
    mutationFn: () => api<Report>('insights/reports/', { method: 'POST', body: {} }),
    onSuccess: (r) => {
      setChosen(r.id)
      void queryClient.invalidateQueries({ queryKey: ['insights', 'reports'] })
      void queryClient.invalidateQueries({ queryKey: ['insights', 'report', r.id] })
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Génération impossible.'),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  const shown = chosen ?? data.results[0]?.id ?? null

  return (
    <section className={styles.page} aria-labelledby="reports-title">
      <div className={styles.toolbar}>
        <div>
          <h2 id="reports-title" className={styles.h2}>
            Rapport hebdomadaire
          </h2>
          <p className={styles.hint}>Envoyé par e-mail chaque lundi à 8 h (heure de Porto-Novo).</p>
        </div>
        <Button variant="secondary" disabled={generate.isPending} onClick={() => generate.mutate()}>
          {generate.isPending ? 'Génération…' : 'Générer le rapport maintenant'}
        </Button>
      </div>
      {shown === null ? (
        <EmptyState
          title="Aucun rapport pour le moment"
          text="Le premier arrive lundi à 8 h. Vous pouvez aussi le générer maintenant."
        />
      ) : (
        <>
          {data.results.length > 1 && (
            <ul className={styles.suggestions} aria-label="Rapports précédents">
              {data.results.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    aria-pressed={r.id === shown}
                    onClick={() => setChosen(r.id)}
                  >
                    {dateFr.format(new Date(r.period_end))}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <Detail id={shown} />
        </>
      )}
    </section>
  )
}
