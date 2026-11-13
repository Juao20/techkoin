import { describe, expect, it } from 'vitest'
import type { VoiceResult } from '@/lib/ai'
import { EMPTY_DRAFT } from './draft'
import { filledLabels, voiceToDraft } from './voice'

const base = {
  available: true as const,
  transcript: 'iPhone 12, 128 giga, batterie 84',
  used_ai: false,
  fields: {
    model_text: 'iphone 12',
    category: 'smartphone',
    storage_gb: 128,
    ram_gb: null,
    battery_health_pct: 84,
    condition_type: 'used',
    grade: 'B',
    accessories: ['charger', 'inconnu'],
    color: null,
    price_fcfa: null,
    defects: 'petite rayure derrière',
  },
  device_model: { slug: 'apple-iphone-12', label: 'Apple iPhone 12', category: 'smartphone' },
} satisfies Extract<VoiceResult, { available: true }>

describe('dictée vers brouillon', () => {
  it('remplit uniquement ce qui a été dit', () => {
    const patch = voiceToDraft(base, EMPTY_DRAFT)
    expect(patch).toMatchObject({
      device_model: 'apple-iphone-12',
      category: 'smartphone',
      storage_gb: '128',
      battery_health_pct: '84',
      condition_type: 'used',
      grade: 'B',
      accessories: ['charger'],
    })
    expect(patch).not.toHaveProperty('ram_gb')
    expect(patch).not.toHaveProperty('price_fcfa')
  })

  it('ajoute le défaut déclaré à la description existante', () => {
    const patch = voiceToDraft(base, { ...EMPTY_DRAFT, description: 'Très propre.' })
    expect(patch.description).toBe('Très propre.\nDéfaut déclaré : petite rayure derrière.')
  })

  it('garde les accessoires déjà cochés', () => {
    const patch = voiceToDraft(base, { ...EMPTY_DRAFT, accessories: ['box'] })
    expect(patch.accessories).toEqual(['box', 'charger'])
  })

  it('liste les champs remplis pour que le vendeur les vérifie', () => {
    expect(filledLabels(voiceToDraft(base, EMPTY_DRAFT))).toEqual(
      expect.arrayContaining(['Modèle', 'Stockage', 'Batterie', 'État', 'Accessoires']),
    )
  })
})
