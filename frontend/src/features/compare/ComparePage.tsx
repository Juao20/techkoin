import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CompareTable, type CompareRow } from '@/components/CompareTable/CompareTable'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { AUTO_NOTICE, type CompareRowApi, type ComparePayload } from '@/lib/ai'
import { ApiError, api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import { useDebounced } from '@/lib/useDebounced'
import { MOBILE_USAGES, PC_USAGES, USAGE_LABELS } from '@/lib/usage'
import styles from './ComparePage.module.css'

function formatCell(row: CompareRowApi, value: string | number | null): string {
  if (value === null || value === undefined || value === '') return '-'
  if (row.key === 'price') return formatFCFA(Number(value))
  if (row.key === 'market_gap') return `${Number(value) > 0 ? '+' : ''}${value} %`
  return String(value)
}

export default function ComparePage() {
  const [params] = useSearchParams()
  const ids = useMemo(
    () =>
      (params.get('ids') ?? '')
        .split(',')
        .map(Number)
        .filter((n) => Number.isInteger(n) && n > 0)
        .slice(0, 3),
    [params],
  )
  const [usage, setUsage] = useState('')
  const [budget, setBudget] = useState('')
  const debouncedBudget = useDebounced(budget, 500)

  const { data, isPending, error } = useQuery({
    queryKey: ['compare', ids, usage, debouncedBudget],
    queryFn: () =>
      api<ComparePayload>('ai/compare/', {
        method: 'POST',
        body: {
          ids,
          usage: usage || null,
          budget: Number(debouncedBudget.replace(/\D/g, '')) || null,
        },
      }),
    enabled: ids.length >= 2,
    retry: false,
  })

  if (ids.length < 2) {
    return (
      <EmptyState
        title="Choisissez au moins deux annonces"
        text="Cochez « Comparer » sur les annonces de la liste, jusqu’à trois."
        action={<Link to="/recherche">Voir les annonces</Link>}
      />
    )
  }

  const category = data?.listings[0]?.category
  const usages = category === 'laptop' || category === 'desktop' ? PC_USAGES : MOBILE_USAGES

  const rows: CompareRow[] =
    data?.rows.map((r) => ({
      label: r.label,
      values: r.values.map((v) => formatCell(r, v)),
      bestIndex: r.best ?? undefined,
    })) ?? []
  const winner = data?.listings.find((l) => l.id === data.verdict.winner_listing_id)

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Comparer des annonces</h1>

      <form className={styles.options} onSubmit={(e) => e.preventDefault()}>
        <label className={styles.field}>
          <span>Usage principal</span>
          <select value={usage} onChange={(e) => setUsage(e.target.value)}>
            <option value="">Peu importe</option>
            {usages.map((u) => (
              <option key={u} value={u}>
                {USAGE_LABELS[u] ?? u}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.field}>
          <span>Budget maximum (FCFA, facultatif)</span>
          <input
            inputMode="numeric"
            value={budget}
            onChange={(e) => setBudget(e.target.value.replace(/\D/g, ''))}
          />
        </label>
      </form>

      {isPending && <p>Comparaison en cours…</p>}
      {error && (
        <EmptyState
          title="Comparaison impossible"
          text={error instanceof ApiError ? error.message : 'Réessayez dans un instant.'}
          action={<Link to="/recherche">Retour aux annonces</Link>}
        />
      )}

      {data && (
        <>
          <section className={styles.verdict} aria-labelledby="verdict">
            <h2 id="verdict" className={styles.h2}>
              Verdict TechKoin
            </h2>
            {winner && (
              <p className={styles.winner}>
                <Tag tone="green">Notre choix</Tag>{' '}
                <Link to={`/annonce/${winner.slug}`}>{winner.title}</Link>
              </p>
            )}
            <p>{data.verdict.summary}</p>
            {data.verdict.reasons.length > 0 && (
              <ul className={styles.list}>
                {data.verdict.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
            {data.verdict.warnings.length > 0 && (
              <ul className={styles.warnings} aria-label="Points d’attention">
                {data.verdict.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
            {data.used_ai && <p className={styles.notice}>{AUTO_NOTICE}</p>}
          </section>

          <section aria-label="Détail par annonce" className={styles.cards}>
            {data.listings.map((l) => {
              const line = data.verdict.per_listing.find((p) => p.listing_id === l.id)
              return (
                <article key={l.id} className={styles.card}>
                  <h3>
                    <Link to={`/annonce/${l.slug}`}>{l.title}</Link>
                  </h3>
                  <p className={styles.price}>{formatFCFA(l.price_fcfa)}</p>
                  {line && (
                    <>
                      <p>Idéal pour : {line.best_for}</p>
                      <p className={styles.notice}>{line.verdict_line}</p>
                    </>
                  )}
                </article>
              )
            })}
          </section>

          <CompareTable
            columns={data.listings.map((l) => ({ id: String(l.id), title: l.title }))}
            rows={rows}
          />
        </>
      )}
    </div>
  )
}
