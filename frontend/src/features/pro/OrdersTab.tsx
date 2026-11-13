import { OrdersList } from '@/features/orders/OrdersList'
import styles from './Pro.module.css'

/** Sales of the shop: the same orders the buyer sees, with the seller's commission on each page. */
export default function OrdersTab() {
  return (
    <>
      <p className={styles.hint}>
        Les ventes avec paiement sécurisé : remise de l’appareil, versement et litiges se suivent
        sur la page de chaque commande.
      </p>
      <OrdersList role="seller" />
    </>
  )
}
