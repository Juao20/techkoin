import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { Radio } from '@/components/Choice/Choice'
import { Input } from '@/components/Input/Input'
import { Tag, type TagTone } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { OPERATORS } from '@/features/orders/types'
import { TestBanner } from '@/features/orders/TestBanner'
import { ApiError, api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import type { User } from '@/lib/types'
import { LoadState, dateFr } from './shared'
import type { SubscriptionState } from './types'
import styles from './Pro.module.css'

const FEATURES = [
  'Radar de la demande : ce que les acheteurs cherchent et que vous n’avez pas',
  'Conseiller prix sur chaque annonce, avec un bouton pour appliquer',
  'Diagnostic du stock dormant et corrections prêtes à appliquer',
  'Rapport hebdomadaire par e-mail, chaque lundi à 8 h',
  'Discussion avec vos chiffres, en français',
  'Optimisation des titres et descriptions en lot',
  'Comparaison de vos annonces à la concurrence',
]
const TONE: Record<string, TagTone> = {
  active: 'green',
  pending: 'yellow',
  failed: 'red',
  expired: 'neutral',
}

export default function SubscriptionTab() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [operator, setOperator] = useState('mtn')
  const [phone, setPhone] = useState('')
  const [phoneError, setPhoneError] = useState('')

  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['shop', 'subscription'],
    queryFn: () => api<SubscriptionState>('shop/subscription/'),
    // A payment waiting for the phone validation settles by itself.
    refetchInterval: (q) => (q.state.data?.latest?.status === 'pending' ? 2500 : false),
  })

  /** The plan lives on the user's shop: refresh it so the whole dashboard follows. */
  const syncPlan = useCallback(
    (next: SubscriptionState) => {
      queryClient.setQueryData(['shop', 'subscription'], next)
      queryClient.setQueryData<{ user: User | null }>(['me'], (me) =>
        me?.user?.shop
          ? { user: { ...me.user, shop: { ...me.user.shop, plan: next.plan } } }
          : (me ?? { user: null }),
      )
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
    },
    [queryClient],
  )
  const shownPlan = user?.shop?.plan
  useEffect(() => {
    if (data && shownPlan && data.plan !== shownPlan) syncPlan(data)
  }, [data, shownPlan, syncPlan])

  const subscribe = useMutation({
    mutationFn: () =>
      api<SubscriptionState>('shop/subscribe/', { method: 'POST', body: { operator, phone } }),
    onSuccess: (next) => {
      syncPlan(next)
      if (next.latest?.status === 'failed') notify('Paiement refusé. Aucun argent n’a été prélevé.')
      else if (next.plan === 'pro') notify('Offre Pro activée.')
    },
    onError: (e) => {
      if (e instanceof ApiError && e.fields.phone) setPhoneError(e.fields.phone)
      else notify(e instanceof ApiError ? e.message : 'Paiement impossible.')
    },
  })
  const settle = useMutation({
    mutationFn: () => api<SubscriptionState>('shop/subscription/settle/', { method: 'POST' }),
    onSuccess: syncPlan,
  })

  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />

  const pro = data.plan === 'pro'
  const pending = data.latest?.status === 'pending'

  function submit(e: FormEvent) {
    e.preventDefault()
    setPhoneError('')
    subscribe.mutate()
  }

  return (
    <>
      <TestBanner />
      <section className={styles.card} aria-labelledby="plan-title">
        <h2 id="plan-title" className={styles.h2}>
          {pro ? 'Vous êtes sur l’offre Pro' : 'Passez à l’offre Pro'}
        </h2>
        {pro && data.plan_expires_at && (
          <p>
            Active jusqu’au <strong>{dateFr.format(new Date(data.plan_expires_at))}</strong>. Payer
            à nouveau prolonge l’abonnement d’un mois.
          </p>
        )}
        <p className={styles.mono}>{formatFCFA(data.price_fcfa)} par mois</p>
        <ul>
          {FEATURES.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      </section>

      {pending ? (
        <section className={styles.card} aria-label="Paiement en cours">
          <h2 className={styles.h2}>Paiement en cours</h2>
          <p>Validez le paiement sur votre téléphone. Cette page se met à jour toute seule.</p>
          {data.latest?.checkout_url && (
            <a
              className={styles.link}
              href={data.latest.checkout_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Continuer vers FedaPay
            </a>
          )}
          {import.meta.env.DEV && (
            <Button variant="secondary" onClick={() => settle.mutate()} disabled={settle.isPending}>
              Valider le paiement simulé (développement)
            </Button>
          )}
        </section>
      ) : (
        <form className={styles.card} onSubmit={submit} noValidate aria-label="Payer l’abonnement">
          <h2 className={styles.h2}>{pro ? 'Prolonger d’un mois' : 'Payer un mois de Pro'}</h2>
          <fieldset className={styles.group}>
            <legend>Opérateur Mobile Money</legend>
            {OPERATORS.map((o) => (
              <Radio
                key={o.value}
                name="operator"
                label={o.label}
                checked={operator === o.value}
                onChange={() => setOperator(o.value)}
              />
            ))}
          </fieldset>
          <Input
            label="Numéro Mobile Money"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            error={phoneError}
            hint="Simulation : un numéro qui finit par 00 est refusé, 77 est validé après 5 secondes, 99 reste en attente."
          />
          <Button type="submit" size="lg" disabled={subscribe.isPending || phone.trim().length < 8}>
            {subscribe.isPending ? 'Paiement…' : `Payer ${formatFCFA(data.price_fcfa)}`}
          </Button>
        </form>
      )}

      <section aria-labelledby="history-title">
        <h2 id="history-title" className={styles.h2}>
          Historique
        </h2>
        {data.history.length === 0 ? (
          <p className={styles.hint}>Aucun paiement pour le moment.</p>
        ) : (
          <ul className={styles.rows}>
            {data.history.map((s) => (
              <li key={s.id} className={styles.row}>
                <div className={styles.rowMain}>
                  <span className={styles.rowTitle}>{formatFCFA(s.amount_fcfa)}</span>
                  <span className={styles.note}>
                    {dateFr.format(new Date(s.created_at))}
                    {s.ends_at ? `, jusqu’au ${dateFr.format(new Date(s.ends_at))}` : ''}
                  </span>
                </div>
                <Tag tone={TONE[s.status] ?? 'neutral'}>{s.status_label}</Tag>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
