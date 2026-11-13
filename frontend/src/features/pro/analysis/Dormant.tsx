import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import { formatFCFA, formatNumber } from '@/lib/format'
import { LoadState, PreviewNotice } from '../shared'
import type { Dormant as DormantData } from '../types'
import styles from '../Pro.module.css'

/** P3: listings online for more than 14 days that convert below the median, and why. */
export default function Dormant() {
  const { user } = useAuth()
  const pro = user?.shop?.plan === 'pro'
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['insights', 'dormant'],
    queryFn: () => api<DormantData>('insights/dormant/'),
  })
  const apply = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api(`insights/listings/${id}/apply/`, { method: 'POST', body }),
    onSuccess: () => {
      notify('Annonce mise à jour.')
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
      void queryClient.invalidateQueries({ queryKey: ['shop', 'stats'] })
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Modification impossible.'),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />

  return (
    <section className={styles.page} aria-labelledby="dormant-title">
      <div>
        <h2 id="dormant-title" className={styles.h2}>
          Stock dormant
        </h2>
        <p className={styles.hint}>
          Annonces en ligne depuis plus de {data.min_days} jours dont le taux de contact est sous la
          médiane de leur catégorie.
        </p>
      </div>
      {data.rows.length === 0 ? (
        <EmptyState
          title="Aucun stock dormant"
          text="Toutes vos annonces anciennes convertissent au moins aussi bien que la médiane."
        />
      ) : (
        <ul className={styles.rows}>
          {data.rows.map((r) => (
            <li key={r.id} className={styles.row}>
              <div className={styles.rowMain}>
                <span className={styles.rowTitle}>
                  <Link to={`/annonce/${r.slug}`}>{r.title}</Link>
                </span>
                <span className={styles.note}>
                  {formatFCFA(r.price_fcfa)} · en ligne depuis {r.days_online} j
                </span>
                <ul className={styles.rows} aria-label="Causes détectées">
                  {r.causes.map((c) => (
                    <li key={c.code} className={styles.actions}>
                      <Tag tone="yellow">{c.label}</Tag>
                      <span className={styles.note}>{c.detail}</span>
                    </li>
                  ))}
                </ul>
                {r.note && <p className={styles.note}>{r.note}</p>}
              </div>
              <dl className={styles.figures}>
                <div>
                  <dt>Vues</dt>
                  <dd>{formatNumber(r.views)}</dd>
                </div>
                <div>
                  <dt>Contacts</dt>
                  <dd>{formatNumber(r.contacts)}</dd>
                </div>
                <div>
                  <dt>Taux de contact</dt>
                  <dd>{String(r.contact_rate).replace('.', ',')} %</dd>
                </div>
                <div>
                  <dt>Médiane</dt>
                  <dd>{String(r.median_contact_rate).replace('.', ',')} %</dd>
                </div>
              </dl>
              {pro && (
                <div className={styles.actions}>
                  {r.advised_price_fcfa && (
                    <Button
                      variant="secondary"
                      disabled={apply.isPending}
                      onClick={() =>
                        apply.mutate({ id: r.id, body: { price_fcfa: r.advised_price_fcfa } })
                      }
                    >
                      Appliquer {formatFCFA(r.advised_price_fcfa)}
                    </Button>
                  )}
                  {r.fix && (
                    <Button
                      variant="secondary"
                      disabled={apply.isPending}
                      onClick={() =>
                        apply.mutate({
                          id: r.id,
                          body: { title: r.fix?.title, description: r.fix?.description },
                        })
                      }
                    >
                      Appliquer le nouveau texte
                    </Button>
                  )}
                </div>
              )}
              {pro && r.fix && (
                <div className={styles.compare}>
                  <div className={styles.after}>
                    <span className={styles.label}>Titre proposé</span>
                    <p className={styles.text}>{r.fix.title}</p>
                    <span className={styles.label}>Description proposée</span>
                    <p className={styles.text}>{r.fix.description}</p>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      <PreviewNotice meta={data} what="diagnostic" />
    </section>
  )
}
