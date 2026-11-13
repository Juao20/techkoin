import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import { STATUS_TONE, type OrderApi } from './types'
import styles from './OrdersList.module.css'

/** The orders of the signed-in account, as buyer and as seller (account tab and shop dashboard). */
export function OrdersList({ role }: { role?: 'buyer' | 'seller' }) {
  const { data, isPending } = useQuery({
    queryKey: ['me', 'orders'],
    queryFn: () => api<OrderApi[]>('me/orders/'),
  })
  if (isPending) return <p>Chargement…</p>
  const orders = (data ?? []).filter((o) => !role || o.role === role)
  if (orders.length === 0) {
    return (
      <EmptyState
        title="Aucune commande"
        text={
          role === 'seller'
            ? 'Les achats avec paiement sécurisé de vos annonces apparaîtront ici.'
            : 'Utilisez « Payer en sécurité » sur une annonce pour acheter avec séquestre.'
        }
        action={
          role === 'seller' ? undefined : (
            <Link to="/recherche?secure_payment=1">Annonces à paiement sécurisé</Link>
          )
        }
      />
    )
  }
  return (
    <ul className={styles.orders}>
      {orders.map((o) => (
        <li key={o.id} className={styles.order}>
          <div>
            <Link to={`/commande/${o.id}`} className={styles.link}>
              {o.listing.title}
            </Link>
            <p className={styles.meta}>
              {o.role === 'seller' ? 'Vente' : 'Achat'} · {formatFCFA(o.amount_fcfa)}
            </p>
          </div>
          <Tag tone={STATUS_TONE[o.status]}>{o.status_label}</Tag>
        </li>
      ))}
    </ul>
  )
}
