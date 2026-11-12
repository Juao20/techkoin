import styles from './SafetyPage.module.css'

export default function SafetyPage() {
  return (
    <article className={styles.page}>
      <h1>Conseils de sécurité</h1>
      <p>
        TechKoin met en relation acheteurs et vendeurs. La vente se conclut entre vous : quelques
        réflexes évitent la plupart des problèmes.
      </p>

      <h2>Avant la rencontre</h2>
      <ul>
        <li>
          Posez vos questions par WhatsApp et demandez des photos ou une vidéo de l’appareil allumé.
        </li>
        <li>Méfiez-vous d’un prix très inférieur au marché.</li>
        <li>Refusez de payer à l’avance, y compris des « frais de réservation ».</li>
      </ul>

      <h2>Pendant la rencontre</h2>
      <ul>
        <li>
          Retrouvez-vous dans un lieu public et fréquenté, de jour, de préférence dans une boutique.
        </li>
        <li>
          Allumez l’appareil et testez l’écran, la batterie, les ports, les caméras et le réseau.
        </li>
        <li>Pour un téléphone, composez *#06# et comparez l’IMEI affiché à celui de l’annonce.</li>
        <li>
          Vérifiez que le compte du vendeur (iCloud, Google) est bien retiré : sinon l’appareil
          restera inutilisable.
        </li>
        <li>Pour un ordinateur, vérifiez le numéro de série et l’état de la batterie.</li>
      </ul>

      <h2>Après l’achat</h2>
      <ul>
        <li>Gardez la facture ou un reçu signé avec l’identité du vendeur.</li>
        <li>Réinitialisez l’appareil et changez les mots de passe.</li>
      </ul>

      <h2>Pour les vendeurs</h2>
      <ul>
        <li>Retirez vos comptes et sauvegardez vos données avant la vente.</li>
        <li>Ne communiquez jamais un code reçu par SMS à un acheteur.</li>
        <li>Décrivez honnêtement l’état : une note d’état fidèle évite les litiges.</li>
      </ul>
    </article>
  )
}
