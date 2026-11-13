import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Select } from '@/components/Select/Select'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import { LoadState } from '../shared'
import type { Competition as CompetitionData, ShopStats } from '../types'
import styles from '../Pro.module.css'

const KIND: Record<string, string> = {
  price: 'Prix',
  warranty: 'Garantie',
  photos: 'Photos',
  accessories: 'Accessoires',
  description: 'Description',
}

function Result({ id }: { id: number }) {
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['insights', 'competition', id],
    queryFn: () => api<CompetitionData>(`insights/competition/${id}/`),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  if (data.competitors.length === 0) {
    return (
      <EmptyState
        title="Pas de concurrente proche"
        text={data.note ?? 'Aucune annonce comparable pour le moment.'}
      />
    )
  }
  return (
    <>
      <section className={styles.card} aria-labelledby="why-title">
        <h3 id="why-title" className={styles.h2}>
          Pourquoi un acheteur pourrait les préférer
        </h3>
        <p>{data.why_them}</p>
        <ul className={styles.rows} aria-label="Actions conseillées">
          {data.actions.map((a) => (
            <li key={a.text} className={styles.actions}>
              <Tag tone="green">{KIND[a.kind] ?? a.kind}</Tag>
              <span>{a.text}</span>
            </li>
          ))}
        </ul>
        <p className={styles.note}>
          {data.used_ai
            ? 'Analyse rédigée par l’IA à partir des faits ci-dessous.'
            : 'Analyse calculée à partir des faits ci-dessous.'}
        </p>
      </section>
      <ul className={styles.rows} aria-label="Annonces concurrentes">
        {data.competitors.map((c) => (
          <li key={c.id} className={styles.row}>
            <div className={styles.rowMain}>
              <span className={styles.rowTitle}>
                <Link to={`/annonce/${c.slug}`}>{c.titre}</Link>
              </span>
              <span className={styles.note}>
                {c.shop ?? 'Particulier'} · {c.city}
              </span>
            </div>
            <dl className={styles.figures}>
              <div>
                <dt>Prix</dt>
                <dd>{formatFCFA(c.prix_fcfa)}</dd>
              </div>
              <div>
                <dt>Garantie</dt>
                <dd>{c.garantie_mois ? `${c.garantie_mois} mois` : 'aucune'}</dd>
              </div>
              <div>
                <dt>Photos</dt>
                <dd>{c.photos}</dd>
              </div>
              <div>
                <dt>Accessoires</dt>
                <dd>{c.accessoires.join(', ') || 'aucun'}</dd>
              </div>
            </dl>
          </li>
        ))}
      </ul>
    </>
  )
}

/** P7: the three closest rivals of one of your listings. */
export default function Competition() {
  const [id, setId] = useState('')
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['shop', 'stats', 30],
    queryFn: () => api<ShopStats>('shop/stats/', { query: { period: 30 } }),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  const active = data.listings.filter((l) => l.status === 'active')

  return (
    <section className={styles.page} aria-labelledby="comp-title">
      <div>
        <h2 id="comp-title" className={styles.h2}>
          Comparer à la concurrence
        </h2>
        <p className={styles.hint}>
          Choisissez une annonce : vous voyez les 3 annonces concurrentes les plus proches et ce qui
          peut faire pencher un acheteur de leur côté.
        </p>
      </div>
      {active.length === 0 ? (
        <EmptyState title="Aucune annonce en ligne" text="Publiez une annonce pour la comparer." />
      ) : (
        <>
          <Select
            label="Mon annonce"
            placeholder="Choisir une annonce"
            value={id || undefined}
            onValueChange={setId}
            options={active.map((l) => ({ value: String(l.id), label: l.title }))}
          />
          {id && <Result id={Number(id)} />}
        </>
      )}
    </section>
  )
}
