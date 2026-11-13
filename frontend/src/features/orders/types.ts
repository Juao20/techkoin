export type OrderStatus =
  | 'created'
  | 'payment_pending'
  | 'paid_held'
  | 'handed_over'
  | 'released'
  | 'disputed'
  | 'refunded'
  | 'cancelled'

export type OrderApi = {
  id: number
  status: OrderStatus
  status_label: string
  role: 'buyer' | 'seller' | 'moderator'
  listing: { id: number; slug: string; title: string; thumb: string | null; city: string }
  amount_fcfa: number
  commission_fcfa: number | null
  seller_payout_fcfa: number | null
  delivery_mode: 'meetup' | 'delivery'
  meetup_note: string
  payment_expires_at: string | null
  handed_over_at: string | null
  buyer_confirmed_at: string | null
  auto_release_at: string | null
  dispute_reason: string
  is_sandbox: boolean
  created_at: string
  history: Array<{ from: string; to: OrderStatus; note: string; at: string }>
  checkout_url: string
  provider: 'simulator' | 'fedapay'
  seller_name: string
  actions: {
    edit: boolean
    pay: boolean
    cancel: boolean
    hand_over: boolean
    confirm: boolean
    dispute: boolean
  }
}

export const OPERATORS = [
  { value: 'mtn', label: 'MTN MoMo' },
  { value: 'moov', label: 'Moov Money' },
  { value: 'celtiis', label: 'Celtiis Cash' },
] as const

export const STATUS_TONE: Record<OrderStatus, 'neutral' | 'green' | 'yellow' | 'red'> = {
  created: 'neutral',
  payment_pending: 'yellow',
  paid_held: 'yellow',
  handed_over: 'yellow',
  released: 'green',
  disputed: 'red',
  refunded: 'neutral',
  cancelled: 'neutral',
}

/** What each state means for the person looking at the order. */
export function nextStep(order: OrderApi): string {
  const { status, role } = order
  const buyer = role === 'buyer'
  switch (status) {
    case 'created':
      return buyer
        ? 'Choisissez votre opérateur et payez : l’argent reste en séquestre.'
        : 'En attente du paiement de l’acheteur.'
    case 'payment_pending':
      return 'Validez le paiement sur votre téléphone. Cette page se met à jour toute seule.'
    case 'paid_held':
      return buyer
        ? 'Paiement reçu. Retrouvez le vendeur, vérifiez l’appareil, puis attendez qu’il signale la remise.'
        : 'Le paiement est en séquestre. Remettez l’appareil à l’acheteur puis signalez-le ici.'
    case 'handed_over':
      return buyer
        ? 'Vérifiez l’appareil. Confirmez la réception, ou ouvrez un litige. Sans réponse, les fonds sont versés automatiquement.'
        : 'En attente de la confirmation de l’acheteur. Les fonds vous seront versés automatiquement à l’échéance.'
    case 'released':
      return buyer
        ? 'Achat terminé. Les fonds ont été versés au vendeur.'
        : 'Les fonds vous ont été versés.'
    case 'disputed':
      return 'Un modérateur TechKoin examine le litige et décidera à qui reviennent les fonds.'
    case 'refunded':
      return 'La commande a été remboursée à l’acheteur.'
    case 'cancelled':
      return 'La commande est annulée. Aucun argent n’a été prélevé.'
  }
}
