import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useParams } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Radio } from '@/components/Choice/Choice'
import { Dialog } from '@/components/Dialog/Dialog'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Input, Textarea } from '@/components/Input/Input'
import { Tag } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import { TestBanner } from './TestBanner'
import { OPERATORS, STATUS_TONE, nextStep, type OrderApi } from './types'
import styles from './OrderPage.module.css'

const DATE = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })

export default function OrderPage() {
  const { id } = useParams()
  const { user, loading } = useAuth()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [operator, setOperator] = useState('mtn')
  const [phone, setPhone] = useState('')
  const [phoneError, setPhoneError] = useState('')
  const [delivery, setDelivery] = useState<'meetup' | 'delivery'>('meetup')
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')

  const key = ['order', id]
  const {
    data: order,
    isPending,
    error,
  } = useQuery({
    queryKey: key,
    queryFn: () => api<OrderApi>(`orders/${id}/`),
    enabled: Boolean(user),
    // A payment waiting for the phone validation refreshes by itself.
    refetchInterval: (q) => (q.state.data?.status === 'payment_pending' ? 2500 : false),
  })

  const refresh = (data: OrderApi) => queryClient.setQueryData(key, data)
  const onError = (e: unknown) => notify(e instanceof ApiError ? e.message : 'Action impossible.')

  const pay = useMutation({
    mutationFn: async () => {
      if (order?.actions.edit) {
        await api(`orders/${id}/`, {
          method: 'PATCH',
          body: { delivery_mode: delivery, meetup_note: note },
        })
      }
      return api<OrderApi>(`orders/${id}/pay/`, { method: 'POST', body: { operator, phone } })
    },
    onSuccess: refresh,
    onError: (e) => {
      if (e instanceof ApiError && e.fields.phone) setPhoneError(e.fields.phone)
      else onError(e)
    },
  })
  const act = (verb: string, body?: unknown) =>
    api<OrderApi>(`orders/${id}/${verb}/`, { method: 'POST', body })
  const cancel = useMutation({ mutationFn: () => act('cancel'), onSuccess: refresh, onError })
  const handOver = useMutation({
    mutationFn: () => act('handed-over'),
    onSuccess: refresh,
    onError,
  })
  const confirm = useMutation({ mutationFn: () => act('confirm'), onSuccess: refresh, onError })
  const dispute = useMutation({
    mutationFn: () => act('dispute', { reason }),
    onSuccess: refresh,
    onError,
  })
  const settle = useMutation({
    mutationFn: () => act('simulator-settle'),
    onSuccess: refresh,
    onError,
  })

  if (loading) return <p>Chargement…</p>
  if (!user) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />
  if (isPending) return <p>Chargement de la commande…</p>
  if (error || !order) {
    return (
      <EmptyState
        title="Commande introuvable"
        text="Elle n’existe pas ou ne vous concerne pas."
        action={<Link to="/compte">Mes commandes</Link>}
      />
    )
  }

  const a = order.actions
  const waiting = order.status === 'payment_pending'
  const seller = order.role === 'seller'

  function submitPay(e: FormEvent) {
    e.preventDefault()
    setPhoneError('')
    pay.mutate()
  }

  return (
    <div className={styles.page}>
      <TestBanner />
      <header className={styles.head}>
        <div>
          <h1 className={styles.title}>Commande n° {order.id}</h1>
          <p className={styles.meta}>
            <Link to={`/annonce/${order.listing.slug}`}>{order.listing.title}</Link>
            {' · '}
            {seller ? 'Vous vendez' : `Vendeur : ${order.seller_name}`}
          </p>
        </div>
        <Tag tone={STATUS_TONE[order.status]}>{order.status_label}</Tag>
      </header>

      <p className={styles.next} role="status">
        {nextStep(order)}
      </p>

      <section className={styles.summary} aria-label="Montants">
        <dl>
          <dt>Prix</dt>
          <dd>{formatFCFA(order.amount_fcfa)}</dd>
          {order.commission_fcfa !== null && order.seller_payout_fcfa !== null && (
            <>
              <dt>Commission TechKoin</dt>
              <dd>{formatFCFA(order.commission_fcfa)}</dd>
              <dt>Vous recevez</dt>
              <dd>{formatFCFA(order.seller_payout_fcfa)}</dd>
            </>
          )}
          <dt>Remise</dt>
          <dd>
            {order.delivery_mode === 'meetup' ? 'En main propre' : 'Livraison'}
            {order.meetup_note ? `, ${order.meetup_note}` : ''}
          </dd>
          {order.auto_release_at && order.status === 'handed_over' && (
            <>
              <dt>Versement automatique</dt>
              <dd>{DATE.format(new Date(order.auto_release_at))}</dd>
            </>
          )}
        </dl>
      </section>

      {a.pay && (
        <form className={styles.card} onSubmit={submitPay} noValidate>
          <h2 className={styles.h2}>Payer en sécurité</h2>
          <p className={styles.hint}>
            L’argent est gardé par TechKoin et n’est versé au vendeur qu’après votre confirmation.
          </p>
          <fieldset className={styles.group}>
            <legend>Remise de l’appareil</legend>
            <Radio
              name="delivery"
              label="En main propre"
              checked={delivery === 'meetup'}
              onChange={() => setDelivery('meetup')}
            />
            <Radio
              name="delivery"
              label="Livraison"
              checked={delivery === 'delivery'}
              onChange={() => setDelivery('delivery')}
            />
          </fieldset>
          <Input
            label="Lieu ou précisions (facultatif)"
            value={note}
            maxLength={300}
            onChange={(e) => setNote(e.target.value)}
          />
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
            hint={
              order.provider === 'simulator'
                ? 'Simulation : un numéro qui finit par 00 est refusé, 77 est validé après 5 secondes, 99 reste en attente.'
                : 'Vous validerez le paiement sur la page sécurisée de FedaPay.'
            }
          />
          <Button type="submit" size="lg" disabled={pay.isPending || phone.trim().length < 8}>
            {pay.isPending ? 'Paiement…' : `Payer ${formatFCFA(order.amount_fcfa)}`}
          </Button>
        </form>
      )}

      {waiting && (
        <section className={styles.card} aria-label="Paiement en cours">
          <h2 className={styles.h2}>Paiement en cours</h2>
          {order.checkout_url && (
            <a
              className={styles.link}
              href={order.checkout_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              Continuer vers FedaPay
            </a>
          )}
          {import.meta.env.DEV && order.provider === 'simulator' && (
            <Button variant="secondary" onClick={() => settle.mutate()} disabled={settle.isPending}>
              Valider le paiement simulé (développement)
            </Button>
          )}
        </section>
      )}

      <div className={styles.actions}>
        {a.hand_over && (
          <Button size="lg" onClick={() => handOver.mutate()} disabled={handOver.isPending}>
            J’ai remis l’appareil
          </Button>
        )}
        {a.confirm && (
          <Button size="lg" onClick={() => confirm.mutate()} disabled={confirm.isPending}>
            Confirmer la réception
          </Button>
        )}
        {a.dispute && (
          <Dialog
            trigger={<Button variant="secondary">Ouvrir un litige</Button>}
            title="Ouvrir un litige"
            description="Décrivez le problème. Un modérateur décidera à qui reviennent les fonds."
          >
            <form
              className={styles.dispute}
              onSubmit={(e) => {
                e.preventDefault()
                dispute.mutate()
              }}
            >
              <Textarea
                label="Ce qui ne va pas"
                rows={4}
                maxLength={1000}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <Button
                type="submit"
                variant="danger"
                disabled={dispute.isPending || reason.trim().length < 10}
              >
                Envoyer le litige
              </Button>
            </form>
          </Dialog>
        )}
        {a.cancel && (
          <Button variant="ghost" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
            Annuler la commande
          </Button>
        )}
      </div>

      {order.dispute_reason && (
        <p className={styles.dispute} role="note">
          Motif du litige : {order.dispute_reason}
        </p>
      )}

      <section aria-labelledby="timeline">
        <h2 id="timeline" className={styles.h2}>
          Chronologie
        </h2>
        <ol className={styles.timeline}>
          {order.history.map((h, i) => (
            <li key={i}>
              <span className={styles.when}>{DATE.format(new Date(h.at))}</span>
              <span>{h.note || h.to}</span>
            </li>
          ))}
        </ol>
      </section>
    </div>
  )
}
