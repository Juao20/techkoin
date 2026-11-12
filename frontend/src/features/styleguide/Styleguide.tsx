import { useState, type ReactNode } from 'react'
import { MagnifyingGlass, Heart } from '@phosphor-icons/react'
import { Button } from '@/components/Button/Button'
import { Checkbox, Radio } from '@/components/Choice/Choice'
import { CompareTable } from '@/components/CompareTable/CompareTable'
import { Dialog } from '@/components/Dialog/Dialog'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { GradeMark } from '@/components/GradeMark/GradeMark'
import { Input, Textarea } from '@/components/Input/Input'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { Popover } from '@/components/Popover/Popover'
import { PriceRange } from '@/components/PriceRange/PriceRange'
import { RangeSlider } from '@/components/RangeSlider/RangeSlider'
import { ScoreBar } from '@/components/ScoreBar/ScoreBar'
import { Select } from '@/components/Select/Select'
import { SpecTable } from '@/components/SpecTable/SpecTable'
import { Stepper } from '@/components/Stepper/Stepper'
import { Tabs } from '@/components/Tabs/Tabs'
import { Tag } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { formatFCFA } from '@/lib/format'
import styles from './Styleguide.module.css'

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className={styles.section}>
      <h2>{title}</h2>
      <div className={styles.stack}>{children}</div>
    </section>
  )
}

export default function Styleguide() {
  const [price, setPrice] = useState<[number, number]>([150000, 300000])
  const [city, setCity] = useState<string>()
  const [compared, setCompared] = useState(false)
  const { notify } = useToast()

  return (
    <main className={styles.page}>
      <h1>Styleguide TechKoin</h1>
      <p className="text-2">
        Page réservée au développement. Elle présente les composants de base et leurs variantes.
      </p>

      <Section title="Couleurs">
        <div className={styles.swatches}>
          {[
            ['--bg', 'Fond de page'],
            ['--surface', 'Surface'],
            ['--surface-2', 'Surface 2'],
            ['--ink', 'Encre'],
            ['--ink-2', 'Encre 2'],
            ['--line', 'Filet'],
            ['--line-strong', 'Filet fort'],
            ['--green', 'Vert'],
            ['--green-tint', 'Vert clair'],
            ['--yellow', 'Jaune'],
            ['--yellow-tint', 'Jaune clair'],
            ['--red', 'Rouge'],
            ['--red-tint', 'Rouge clair'],
          ].map(([token, name]) => (
            <div key={token} className={styles.swatch}>
              <span className={styles.chip} style={{ background: `var(${token})` }} />
              <span className="small">{name}</span>
              <code className="micro mono text-2">{token}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Typographie">
        <h1>Titre H1 : 40 px (30 px sur mobile)</h1>
        <h2>Titre H2 : 28 px</h2>
        <h3>Titre H3 : 20 px</h3>
        <p>Corps de texte en IBM Plex Sans, 16 px, interligne 1,5.</p>
        <p className="small text-2">Texte secondaire, 14 px.</p>
        <p className="mono">16 Go · 512 Go SSD · i5 11e gén. · {formatFCFA(185000)}</p>
      </Section>

      <Section title="Boutons">
        <div className={styles.row}>
          <Button>Publier l'annonce</Button>
          <Button variant="secondary">Comparer</Button>
          <Button variant="ghost">Voir les détails</Button>
          <Button variant="danger">Supprimer</Button>
          <Button disabled>Désactivé</Button>
        </div>
        <div className={styles.row}>
          <Button size="lg">
            <MagnifyingGlass size={20} /> Rechercher
          </Button>
          <Button variant="secondary" size="lg">
            <Heart size={20} /> Favori
          </Button>
        </div>
      </Section>

      <Section title="Champs">
        <div className={styles.form}>
          <Input
            label="Modèle"
            placeholder="iPhone 13, ThinkPad T14..."
            hint="Commencez à taper pour voir les suggestions."
          />
          <Input
            label="Prix"
            defaultValue="abc"
            error="Saisissez un montant en FCFA, sans lettres."
          />
          <Select
            label="Ville"
            value={city}
            onValueChange={setCity}
            options={[
              { value: 'cotonou', label: 'Cotonou' },
              { value: 'abomey-calavi', label: 'Abomey-Calavi' },
              { value: 'porto-novo', label: 'Porto-Novo' },
              { value: 'parakou', label: 'Parakou' },
            ]}
          />
          <Textarea label="Description" placeholder="État, accessoires, défauts éventuels." />
          <div className={styles.choices}>
            <Checkbox label="Avec facture" defaultChecked />
            <Checkbox label="Avec garantie" />
          </div>
          <div className={styles.choices}>
            <Radio name="cond" label="Occasion" defaultChecked />
            <Radio name="cond" label="Reconditionné" />
          </div>
          <RangeSlider
            label="Budget"
            min={0}
            max={1000000}
            step={5000}
            value={price}
            onValueChange={setPrice}
            format={formatFCFA}
          />
        </div>
      </Section>

      <Section title="Étiquettes et notes d'état">
        <div className={styles.row}>
          <Tag>QWERTY</Tag>
          <Tag tone="green">Boutique vérifiée</Tag>
          <Tag tone="yellow">Bonne affaire</Tag>
          <Tag tone="red">Au-dessus du marché</Tag>
          <Tag>Garantie 6 mois</Tag>
        </div>
        <div className={styles.row}>
          <GradeMark grade="A" />
          <GradeMark grade="B" />
          <GradeMark grade="C" />
        </div>
      </Section>

      <Section title="Carte d'annonce">
        <div className={styles.grid}>
          <ListingCard
            compared={compared}
            onCompareChange={setCompared}
            listing={{
              id: 'demo-1',
              href: '#',
              title: 'HP ProBook 450 G8 15,6 pouces',
              specs: '16 Go · 512 Go SSD · i5 11e gén.',
              priceFcfa: 185000,
              priceBadge: 'good_deal',
              city: 'Cotonou',
              age: 'il y a 2 jours',
              grade: 'A',
              keyboard: 'AZERTY',
              verifiedSeller: true,
            }}
          />
          <ListingCard
            listing={{
              id: 'demo-2',
              href: '#',
              title: 'iPhone 12 128 Go noir',
              specs: '128 Go · batterie 84 %',
              priceFcfa: 260000,
              priceBadge: 'above_market',
              city: 'Abomey-Calavi',
              age: 'il y a 5 jours',
              grade: 'B',
            }}
          />
        </div>
      </Section>

      <Section title="Fourchette de prix">
        <PriceRange low={170000} high={195000} price={185000} />
      </Section>

      <Section title="Scores d'usage">
        <ScoreBar label="Bureautique" score={9} />
        <ScoreBar label="Développement" score={7} />
        <ScoreBar label="Jeux" score={3} />
      </Section>

      <Section title="Fiche technique">
        <SpecTable
          groups={[
            {
              title: 'Performances',
              rows: [
                { label: 'Processeur', value: 'Intel Core i5-1135G7' },
                { label: 'Mémoire', value: '16 Go' },
                { label: 'Stockage', value: '512 Go SSD' },
              ],
            },
            {
              title: 'Écran',
              rows: [
                { label: 'Taille', value: '15,6 pouces' },
                { label: 'Résolution', value: '1920 x 1080' },
              ],
            },
          ]}
        />
      </Section>

      <Section title="Comparaison">
        <CompareTable
          columns={[
            { id: 'a', title: 'HP ProBook 450' },
            { id: 'b', title: 'Dell Latitude 5420' },
          ]}
          rows={[
            { label: 'Prix', values: [formatFCFA(185000), formatFCFA(200000)], bestIndex: 0 },
            { label: 'Mémoire', values: ['16 Go', '16 Go'] },
            { label: 'Stockage', values: ['512 Go SSD', '256 Go SSD'], bestIndex: 0 },
            { label: 'Clavier', values: ['AZERTY', 'QWERTY'], bestIndex: 0 },
          ]}
        />
      </Section>

      <Section title="Onglets">
        <Tabs
          items={[
            {
              value: 'overview',
              label: "Vue d'ensemble",
              content: <p>Contenu de la vue d'ensemble.</p>,
            },
            { value: 'listings', label: 'Annonces', content: <p>Liste des annonces.</p> },
            { value: 'analysis', label: 'Analyse', content: <p>Analyse du marché.</p> },
          ]}
        />
      </Section>

      <Section title="Étapes de publication">
        <Stepper
          current={3}
          steps={[
            'Modèle',
            'État',
            'Caractéristiques',
            'Photos',
            'Prix',
            'Description',
            'Récapitulatif',
          ]}
        />
      </Section>

      <Section title="Fenêtres et notifications">
        <div className={styles.row}>
          <Dialog
            trigger={<Button variant="secondary">Ouvrir une fenêtre</Button>}
            title="Signaler cette annonce"
            description="Dites-nous ce qui ne va pas. Un modérateur examinera votre signalement."
          >
            <Textarea label="Détails" />
            <Button>Envoyer le signalement</Button>
          </Dialog>
          <Popover trigger={<Button variant="secondary">Ouvrir un panneau</Button>}>
            <p className="small">Vérifiez l'IMEI avec le code *#06# avant de payer.</p>
          </Popover>
          <Button variant="secondary" onClick={() => notify('Annonce ajoutée aux favoris.')}>
            Afficher une notification
          </Button>
        </div>
      </Section>

      <Section title="État vide">
        <EmptyState
          title="Aucune annonce trouvée"
          text="Modifiez vos filtres ou créez une alerte pour être prévenu des nouvelles annonces."
          action={<Button variant="secondary">Créer une alerte</Button>}
        />
      </Section>
    </main>
  )
}
