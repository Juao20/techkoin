import type { VoiceResult } from '@/lib/ai'
import type { Category } from '@/lib/types'
import type { Draft } from './draft'

type Available = Extract<VoiceResult, { available: true }>

const ACCESSORIES = new Set(['charger', 'box', 'cable', 'case', 'earphones', 'invoice'])
const CONDITIONS = new Set(['new_sealed', 'new_open', 'refurbished', 'used'])

/** Turns the dictation into draft fields. Only what was said is filled; the seller checks it. */
export function voiceToDraft(result: Available, current: Draft): Partial<Draft> {
  const f = result.fields
  const patch: Partial<Draft> = {}
  if (result.device_model) {
    patch.device_model = result.device_model.slug
    patch.device_label = result.device_model.label
    patch.category = result.device_model.category as Category
    patch.custom_model_name = ''
  } else if (f.category) {
    patch.category = f.category as Category
  }
  if (f.storage_gb) patch.storage_gb = String(f.storage_gb)
  if (f.ram_gb) patch.ram_gb = String(f.ram_gb)
  if (f.battery_health_pct) patch.battery_health_pct = String(f.battery_health_pct)
  if (f.condition_type && CONDITIONS.has(f.condition_type)) {
    patch.condition_type = f.condition_type as Draft['condition_type']
  }
  if (f.grade === 'A' || f.grade === 'B' || f.grade === 'C') patch.grade = f.grade
  const accessories = f.accessories.filter((a) => ACCESSORIES.has(a))
  if (accessories.length > 0)
    patch.accessories = [...new Set([...current.accessories, ...accessories])]
  if (f.color) patch.color = f.color
  if (f.price_fcfa) patch.price_fcfa = String(f.price_fcfa)
  if (f.defects) {
    const note = `Défaut déclaré : ${f.defects}.`
    patch.description = current.description ? `${current.description}\n${note}` : note
  }
  return patch
}

const LABELS: Record<string, string> = {
  device_model: 'Modèle',
  storage_gb: 'Stockage',
  ram_gb: 'Mémoire vive',
  battery_health_pct: 'Batterie',
  condition_type: 'État',
  grade: 'Note d’état',
  accessories: 'Accessoires',
  color: 'Couleur',
  price_fcfa: 'Prix',
  description: 'Défaut déclaré',
}

export function filledLabels(patch: Partial<Draft>): string[] {
  return Object.keys(patch)
    .map((k) => LABELS[k])
    .filter((l): l is string => Boolean(l))
}
