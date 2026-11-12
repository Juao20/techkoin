import type { Category, ListingDetailApi } from '@/lib/types'
import { DEFAULT_ANSWERS, type Grade, type GradeAnswers } from './grade'

/** Form state of the publication wizard. Strings stay strings until `toPayload`. */
export type Draft = {
  category: Category | ''
  device_model: string
  device_label: string
  custom_brand: string
  custom_model_name: string
  condition_type: 'new_sealed' | 'new_open' | 'refurbished' | 'used'
  grade: Grade | ''
  answers: GradeAnswers
  battery_health_pct: string
  ram_gb: string
  storage_gb: string
  storage_type: string
  color: string
  processor: number | null
  processor_label: string
  gpu: number | null
  gpu_label: string
  keyboard_layout: string
  network_5g: boolean
  dual_sim: boolean
  carrier_unlocked: boolean
  account_removed: boolean
  biometrics_ok: boolean
  screen_original: boolean
  cellular: boolean
  stylus_included: boolean
  price_fcfa: string
  negotiable: boolean
  city: string
  quartier: string
  accessories: string[]
  warranty_months: string
  provenance: string
  imei_or_serial: string
  description: string
}

export const EMPTY_DRAFT: Draft = {
  category: '',
  device_model: '',
  device_label: '',
  custom_brand: '',
  custom_model_name: '',
  condition_type: 'used',
  grade: 'A', // matches DEFAULT_ANSWERS; the seller adjusts it through the checklist
  answers: DEFAULT_ANSWERS,
  battery_health_pct: '',
  ram_gb: '',
  storage_gb: '',
  storage_type: '',
  color: '',
  processor: null,
  processor_label: '',
  gpu: null,
  gpu_label: '',
  keyboard_layout: '',
  network_5g: false,
  dual_sim: false,
  carrier_unlocked: true,
  account_removed: false,
  biometrics_ok: true,
  screen_original: true,
  cellular: false,
  stylus_included: false,
  price_fcfa: '',
  negotiable: false,
  city: '',
  quartier: '',
  accessories: [],
  warranty_months: '0',
  provenance: '',
  imei_or_serial: '',
  description: '',
}

const num = (s: string): number | undefined => {
  const n = Number(s.replace(/\s/g, ''))
  return s.trim() !== '' && Number.isFinite(n) ? n : undefined
}

export const isNew = (d: Draft) =>
  d.condition_type === 'new_sealed' || d.condition_type === 'new_open'
export const isComputer = (d: Draft) => d.category === 'laptop' || d.category === 'desktop'
export const isMobile = (d: Draft) => d.category === 'smartphone' || d.category === 'tablet'

/** Only sends what the seller filled in, so a partial draft can be saved at every step. */
export function toPayload(d: Draft): Record<string, unknown> {
  const p: Record<string, unknown> = {
    condition_type: d.condition_type,
    grade: isNew(d) ? '' : d.grade,
    negotiable: d.negotiable,
    accessories: d.accessories,
  }
  if (d.category) p.category = d.category
  if (d.device_model) p.device_model = d.device_model
  else if (d.custom_model_name) {
    p.custom_model_name = d.custom_model_name
    if (d.custom_brand) p.brand = d.custom_brand
  }
  const numeric: Array<[string, string]> = [
    ['price_fcfa', d.price_fcfa],
    ['ram_gb', d.ram_gb],
    ['storage_gb', d.storage_gb],
    ['battery_health_pct', d.battery_health_pct],
    ['warranty_months', d.warranty_months],
  ]
  for (const [key, value] of numeric) {
    const n = num(value)
    if (n !== undefined) p[key] = n
  }
  const text: Array<[string, string]> = [
    ['storage_type', d.storage_type],
    ['color', d.color],
    ['keyboard_layout', d.keyboard_layout],
    ['city', d.city],
    ['quartier', d.quartier],
    ['provenance', d.provenance],
    ['imei_or_serial', d.imei_or_serial.trim()],
    ['description', d.description],
  ]
  for (const [key, value] of text) if (value) p[key] = value
  if (d.processor) p.processor = d.processor
  if (d.gpu) {
    p.gpu = d.gpu
    p.gpu_dedicated = true
  }
  if (isMobile(d)) {
    Object.assign(p, {
      network_5g: d.network_5g,
      dual_sim: d.dual_sim,
      carrier_unlocked: d.carrier_unlocked,
      account_removed: d.account_removed,
      biometrics_ok: d.biometrics_ok,
      screen_original: d.screen_original,
    })
    if (d.category === 'tablet')
      Object.assign(p, { cellular: d.cellular, stylus_included: d.stylus_included })
  }
  return p
}

/** Rebuilds the form from a draft already saved on the server. */
export function fromListing(l: ListingDetailApi): Draft {
  const s = (v: unknown) => (v === null || v === undefined ? '' : String(v))
  return {
    ...EMPTY_DRAFT,
    category: l.category,
    device_model: l.model_slug ?? '',
    device_label: l.title,
    condition_type: l.condition_type as Draft['condition_type'],
    grade: l.grade,
    battery_health_pct: s(l.battery_health_pct),
    ram_gb: s(l.ram_gb),
    storage_gb: s(l.storage_gb),
    storage_type: l.storage_type,
    color: l.color,
    processor_label: l.processor?.name ?? '',
    gpu_label: l.gpu ?? '',
    keyboard_layout: l.keyboard_layout,
    network_5g: l.network_5g,
    dual_sim: l.dual_sim,
    carrier_unlocked: l.carrier_unlocked,
    account_removed: l.account_removed,
    biometrics_ok: l.biometrics_ok,
    screen_original: l.screen_original,
    cellular: l.cellular,
    stylus_included: l.stylus_included,
    price_fcfa: l.price_fcfa ? String(l.price_fcfa) : '',
    negotiable: l.negotiable,
    city: l.city,
    quartier: l.quartier,
    accessories: l.accessories,
    warranty_months: String(l.warranty_months),
    provenance: l.provenance,
    description: l.description,
  }
}
