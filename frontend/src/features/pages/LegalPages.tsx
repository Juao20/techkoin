import { Link } from 'react-router-dom'
import styles from './SafetyPage.module.css'

/** Plain-language legal pages (spec 14). The texts describe what the application really does. */

export function AboutPage() {
  return (
    <article className={styles.page}>
      <h1>À propos de TechKoin</h1>
      <p>
        TechKoin est une place de marché pour acheter et vendre des PC, des smartphones et des
        tablettes, neufs ou d’occasion, entre boutiques et particuliers au Bénin.
      </p>
      <h2>Ce que nous faisons</h2>
      <ul>
        <li>Nous montrons le prix du marché et signalons les prix trop beaux ou trop élevés.</li>
        <li>
          Nous contrôlons les numéros IMEI et examinons les annonces à risque avant leur mise en
          ligne.
        </li>
        <li>
          Nous proposons un paiement avec séquestre : l’argent n’est versé au vendeur qu’après votre
          confirmation.
        </li>
        <li>Nous aidons les boutiques à comprendre la demande et à fixer leurs prix.</li>
      </ul>
      <h2>Ce que nous ne faisons pas</h2>
      <p>
        TechKoin ne vend pas les appareils et ne les livre pas : la vente se conclut entre
        l’acheteur et le vendeur. Lisez nos <Link to="/securite">conseils de sécurité</Link>.
      </p>
      <p>
        Le paiement sécurisé fonctionne pour l’instant en mode test : aucun argent réel n’est
        débité.
      </p>
    </article>
  )
}

export function TermsPage() {
  return (
    <article className={styles.page}>
      <h1>Conditions générales d’utilisation</h1>
      <p>Ces conditions s’appliquent à toute personne qui utilise TechKoin.</p>
      <h2>Votre compte</h2>
      <ul>
        <li>Vous donnez des informations exactes et vous gardez votre mot de passe pour vous.</li>
        <li>Un particulier peut avoir 5 annonces en ligne en même temps.</li>
      </ul>
      <h2>Vos annonces</h2>
      <ul>
        <li>
          Vous ne vendez que des appareils qui vous appartiennent et que vous pouvez remettre.
        </li>
        <li>
          Les informations, les photos et l’état déclaré doivent correspondre à l’appareil. Un
          numéro IMEI ou de série déclaré volé fait retirer l’annonce.
        </li>
        <li>
          TechKoin peut examiner, refuser ou retirer une annonce, par exemple en cas de risque
          d’arnaque, de photo reprise ailleurs ou de coordonnées placées dans le texte.
        </li>
      </ul>
      <h2>Paiement sécurisé</h2>
      <ul>
        <li>
          L’argent est gardé en séquestre. Il est versé au vendeur quand l’acheteur confirme la
          réception, ou automatiquement 48 heures après la remise s’il ne répond pas.
        </li>
        <li>
          L’acheteur peut ouvrir un litige avant le versement. Un modérateur décide alors du
          versement au vendeur ou du remboursement.
        </li>
        <li>
          La commission est de 3 % du prix, avec un minimum de 500 FCFA, payée par le vendeur.
        </li>
        <li>Pendant la période de test, aucun argent réel n’est débité ni versé.</li>
      </ul>
      <h2>Offre Pro des boutiques</h2>
      <p>
        L’abonnement Pro dure un mois et donne accès aux analyses. Il ne se renouvelle pas tout
        seul. Les analyses et les conseils sont des aides à la décision calculées sur les données du
        site : ils ne garantissent aucune vente.
      </p>
      <h2>Responsabilités</h2>
      <p>
        TechKoin met en relation et sécurise le paiement, mais ne garantit pas l’état des appareils
        vendus entre particuliers. En cas de doute, ne payez pas et signalez l’annonce.
      </p>
    </article>
  )
}

export function PrivacyPage() {
  return (
    <article className={styles.page}>
      <h1>Confidentialité</h1>
      <p>Voici ce que TechKoin garde, pourquoi, et pour combien de temps.</p>
      <h2>Ce que nous gardons</h2>
      <ul>
        <li>
          Votre compte : e-mail, téléphone, ville, et pour une boutique les informations de la
          vitrine.
        </li>
        <li>
          Vos annonces, vos favoris, vos alertes et vos commandes. Le numéro IMEI ou de série est
          conservé chiffré, et seule une empreinte sert à repérer les doublons.
        </li>
        <li>
          Des événements d’usage (recherches, vues, clics de contact) sans nom : ils servent aux
          statistiques des annonces et à l’analyse de la demande. Ils sont conservés 18 mois.
        </li>
      </ul>
      <h2>Documents de vérification</h2>
      <p>
        Les pièces d’identité et les documents de boutique sont stockés dans un espace privé, lus
        uniquement par les modérateurs, et supprimés 90 jours après la décision.
      </p>
      <h2>Intelligence artificielle</h2>
      <p>
        Les fonctions d’IA ne reçoivent jamais de nom, de téléphone, d’e-mail ni d’IMEI : seulement
        les caractéristiques d’une annonce ou des chiffres agrégés. Les enregistrements vocaux sont
        supprimés dès qu’ils sont transcrits.
      </p>
      <h2>Vos choix</h2>
      <ul>
        <li>Vous pouvez supprimer vos alertes à tout moment dans votre compte.</li>
        <li>Les cookies servent à la connexion et à compter les visites sans vous identifier.</li>
        <li>Votre numéro n’est montré qu’à un acheteur connecté qui le demande.</li>
      </ul>
    </article>
  )
}
