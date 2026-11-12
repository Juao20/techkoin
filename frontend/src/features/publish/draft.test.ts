import { describe, expect, it } from 'vitest'
import { EMPTY_DRAFT, toPayload, type Draft } from './draft'

const draft = (patch: Partial<Draft>): Draft => ({ ...EMPTY_DRAFT, ...patch })

describe('toPayload', () => {
  it('n’envoie que les champs remplis', () => {
    const p = toPayload(draft({ category: 'laptop' }))
    expect(p.category).toBe('laptop')
    expect(p).not.toHaveProperty('price_fcfa')
    expect(p).not.toHaveProperty('imei_or_serial')
    expect(p).not.toHaveProperty('network_5g')
  })

  it('convertit les nombres saisis avec des espaces', () => {
    const p = toPayload(draft({ category: 'laptop', price_fcfa: '185 000', ram_gb: '16' }))
    expect(p.price_fcfa).toBe(185000)
    expect(p.ram_gb).toBe(16)
  })

  it('vide la note d’état pour un appareil neuf', () => {
    const p = toPayload(draft({ category: 'laptop', condition_type: 'new_sealed', grade: 'A' }))
    expect(p.grade).toBe('')
  })

  it('envoie les champs téléphone seulement pour un téléphone ou une tablette', () => {
    const phone = toPayload(draft({ category: 'smartphone', account_removed: true }))
    expect(phone.account_removed).toBe(true)
    const pc = toPayload(draft({ category: 'laptop', account_removed: true }))
    expect(pc).not.toHaveProperty('account_removed')
  })

  it('utilise le modèle du catalogue ou, à défaut, le modèle saisi', () => {
    expect(
      toPayload(draft({ category: 'smartphone', device_model: 'iphone-13' })).device_model,
    ).toBe('iphone-13')
    const custom = toPayload(
      draft({ category: 'smartphone', custom_brand: 'tecno', custom_model_name: 'Spark Go' }),
    )
    expect(custom.custom_model_name).toBe('Spark Go')
    expect(custom.brand).toBe('tecno')
    expect(custom).not.toHaveProperty('device_model')
  })
})
