import type { SpecGroup } from '@/components/SpecTable/SpecTable'
import { CONDITION_LABELS } from '@/lib/listings'
import type { ListingDetailApi } from '@/lib/types'

const yes = (v: boolean) => (v ? 'Oui' : 'Non')
const PROVENANCE: Record<string, string> = {
  local: 'Locale',
  europe: 'Europe',
  usa: 'États-Unis',
  dubai: 'Dubaï',
  china: 'Chine',
  other: 'Autre',
}
const ACCESSORIES: Record<string, string> = {
  charger: 'Chargeur',
  box: 'Boîte',
  cable: 'Câble',
  case: 'Coque',
  earphones: 'Écouteurs',
  invoice: 'Facture',
}

type Row = { label: string; value: string }

function rows(...entries: Array<[string, string | number | null | undefined | false]>): Row[] {
  return entries
    .filter(([, v]) => v !== null && v !== undefined && v !== '' && v !== false)
    .map(([label, v]) => ({ label, value: String(v) }))
}

export function buildSpecGroups(l: ListingDetailApi): SpecGroup[] {
  const isComputer = l.category === 'laptop' || l.category === 'desktop'
  const isMobile = l.category === 'smartphone' || l.category === 'tablet'
  const groups: SpecGroup[] = []

  groups.push({
    title: 'Général',
    rows: rows(
      ['État', CONDITION_LABELS[l.condition_type] ?? l.condition_type],
      ['Note d’état', l.grade ? `${l.grade}` : ''],
      ['Marque', l.brand],
      ['Couleur', l.color],
      ['Provenance', PROVENANCE[l.provenance] ?? ''],
      ['Garantie', l.warranty_months ? `${l.warranty_months} mois` : 'Aucune'],
    ),
  })

  const hardware = rows(
    ['Processeur', l.processor?.name],
    ['Mémoire vive', l.ram_gb ? `${l.ram_gb} Go` : ''],
    ['Stockage', l.storage_gb ? `${l.storage_gb} Go ${l.storage_type.toUpperCase()}`.trim() : ''],
    ['Carte graphique', l.gpu],
    ['Mémoire vidéo', l.vram_gb ? `${l.vram_gb} Go` : ''],
    ['Système', l.os],
  )
  if (hardware.length) groups.push({ title: 'Performances', rows: hardware })

  const screen = rows(
    ['Taille', l.screen_size_in ? `${l.screen_size_in} pouces` : ''],
    ['Résolution', l.screen_resolution],
    ['Fréquence', l.refresh_rate_hz ? `${l.refresh_rate_hz} Hz` : ''],
    ['Écran tactile', isComputer && l.touchscreen ? 'Oui' : ''],
  )
  if (screen.length) groups.push({ title: 'Écran', rows: screen })

  if (isComputer) {
    groups.push({
      title: 'Ordinateur',
      rows: rows(
        ['Clavier', l.keyboard_layout ? l.keyboard_layout.toUpperCase() : ''],
        ['Clavier rétroéclairé', l.keyboard_backlit ? 'Oui' : ''],
        ['Cycles de batterie', l.battery_cycles],
        ['Autonomie', l.battery_autonomy_h ? `${l.battery_autonomy_h} h` : ''],
        ['Ports', l.ports.join(', ')],
        ['Mémoire extensible', l.ram_upgradable ? 'Oui' : ''],
      ),
    })
  }

  if (isMobile) {
    groups.push({
      title: 'Téléphone et tablette',
      rows: rows(
        ['Santé de la batterie', l.battery_health_pct ? `${l.battery_health_pct} %` : ''],
        ['5G', yes(l.network_5g)],
        ['Double SIM', yes(l.dual_sim)],
        ['eSIM', l.esim ? 'Oui' : ''],
        ['Débloqué tout opérateur', yes(l.carrier_unlocked)],
        ['Compte précédent retiré', yes(l.account_removed)],
        ['Biométrie fonctionnelle', yes(l.biometrics_ok)],
        ['Écran d’origine', yes(l.screen_original)],
        ['Pièces remplacées', l.replaced_parts.length ? l.replaced_parts.join(', ') : 'Aucune'],
        ['Avec carte SIM', l.category === 'tablet' ? yes(l.cellular) : ''],
        ['Stylet inclus', l.stylus_included ? 'Oui' : ''],
        ['Clavier inclus', l.keyboard_included ? 'Oui' : ''],
      ),
    })
  }

  const inBox = l.accessories.map((a) => ACCESSORIES[a] ?? a).join(', ')
  groups.push({ title: 'Dans la boîte', rows: rows(['Accessoires', inBox || 'Appareil seul']) })

  return groups
}
