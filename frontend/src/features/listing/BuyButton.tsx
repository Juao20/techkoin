import { ShieldCheck } from '@phosphor-icons/react'
import { useMutation } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import type { OrderApi } from '@/features/orders/types'
import { ApiError, api } from '@/lib/api'
import type { ListingDetailApi } from '@/lib/types'
import styles from './BuyButton.module.css'

/** « Payer en sécurité »: opens an order whose money stays in escrow until the buyer confirms. */
export function BuyButton({ listing }: { listing: ListingDetailApi }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { notify } = useToast()

  const create = useMutation({
    mutationFn: () =>
      api<OrderApi>('orders/', { method: 'POST', body: { listing_id: listing.id } }),
    onSuccess: (order) => navigate(`/commande/${order.id}`),
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Commande impossible.'),
  })

  if (!listing.accepts_secure_payment || listing.status !== 'active') return null
  return (
    <div className={styles.wrap}>
      <Button
        size="lg"
        variant="secondary"
        disabled={create.isPending}
        onClick={() => {
          if (!user) navigate('/connexion', { state: { from: location.pathname } })
          else create.mutate()
        }}
      >
        <ShieldCheck size={22} aria-hidden /> Payer en sécurité
      </Button>
      <p className={styles.hint}>
        Votre argent reste en séquestre jusqu’à la remise. Mode test : aucun argent réel n’est
        débité.
      </p>
    </div>
  )
}
