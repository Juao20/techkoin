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
import type { Pricing as PricingData, PricingRow } from '../types'
import styles from '../Pro.module.css'

const VERDICT: Record<
  PricingRow['action'],
  { label: string; tone: 'green' | 'yellow' | 'red' | 'neutral' }
> = {
  lower: { label: 'Au-dessus du marché', tone: 'red' },
  raise: { label: 'Sous le marché', tone: 'yellow' },
  keep: { label: 'Prix cohérent', tone: 'green' },
  none: { label: 'Estimation indisponible', tone: 'neutral' },
}

/** P2: where each listing's price stands, and a price to ask (computed, never invented). */
export default function Pricing() {
  const { user } = useAuth()
  const pro = user?.shop?.plan === 'pro'
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['insights', 'pricing'],
    queryFn: () => api<PricingData>('insights/pricing/'),
  })
  const apply = useMutation({
    mutationFn: ({ id, price }: { id: number; price: number }) =>
      api(`insights/listings/${id}/apply/`, { method: 'POST', body: { price_fcfa: price } }),
    onSuccess: () => {
      notify('Prix mis à jour.')
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
      void queryClient.invalidateQueries({ queryKey: ['shop', 'stats'] })
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Modification impossible.'),
  })
  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />

  return (
    <section className={styles.page} aria-labelledby="pricing-title">
      <div>
        <h2 id="pricing-title" className={styles.h2}>
          Conseiller prix
        </h2>
        <p className={styles.hint}>
          Votre prix face à l’estimation du marché. Le prix conseillé est calculé et arrondi à 5 000
          FCFA.
        </p>
      </div>
      {data.rows.length === 0 ? (
        <EmptyState
          title="Aucune annonce en ligne"
          text="Publiez des annonces pour recevoir des conseils de prix."
          action={<Link to="/vendre">Publier une annonce</Link>}
        />
      ) : (
        <ul className={styles.rows}>
          {data.rows.map((r) => {
            const v = VERDICT[r.action]
            return (
              <li key={r.id} className={styles.row}>
                <div className={styles.rowMain}>
                  <span className={styles.rowTitle}>
                    <Link to={`/annonce/${r.slug}`}>{r.title}</Link>
                  </span>
                  <span className={styles.causes}>
                    <Tag tone={v.tone}>{v.label}</Tag>
                    {r.indicative && r.action !== 'none' && <Tag>Estimation indicative</Tag>}
                  </span>
                  <p className={styles.note}>{r.note}</p>
                </div>
                <dl className={styles.figures}>
                  <div>
                    <dt>Votre prix</dt>
                    <dd>{formatFCFA(r.price_fcfa)}</dd>
                  </div>
                  <div>
                    <dt>Estimation</dt>
                    <dd>{r.estimate_fcfa ? formatFCFA(r.estimate_fcfa) : 'n/d'}</dd>
                  </div>
                  <div>
                    <dt>Vues / contacts</dt>
                    <dd>
                      {formatNumber(r.views)} / {formatNumber(r.contacts)}
                    </dd>
                  </div>
                  <div>
                    <dt>Moyenne de la catégorie</dt>
                    <dd>
                      {String(r.category_avg_views).replace('.', ',')} /{' '}
                      {String(r.category_avg_contacts).replace('.', ',')}
                    </dd>
                  </div>
                </dl>
                {pro && (r.action === 'lower' || r.action === 'raise') && r.advised_price_fcfa && (
                  <Button
                    disabled={apply.isPending}
                    onClick={() =>
                      apply.mutate({ id: r.id, price: r.advised_price_fcfa as number })
                    }
                  >
                    Appliquer {formatFCFA(r.advised_price_fcfa)}
                  </Button>
                )}
              </li>
            )
          })}
        </ul>
      )}
      <PreviewNotice meta={data} what="conseil de prix" />
    </section>
  )
}
