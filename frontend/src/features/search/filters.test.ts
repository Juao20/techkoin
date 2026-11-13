import { describe, expect, it } from 'vitest'
import {
  clearFilters,
  countActive,
  parseFilters,
  serializeFilters,
  withFlag,
  withList,
  withPage,
  withSingle,
} from './filters'

const parse = (qs: string) => parseFilters(new URLSearchParams(qs))
const roundTrip = (qs: string) => serializeFilters(parse(qs)).toString()

describe('filtres dans l’URL', () => {
  it('lit les valeurs simples, listes et drapeaux', () => {
    const f = parse('q=iphone&brand=apple,samsung&5g=1&price_max=300000&page=3')
    expect(f.single.q).toBe('iphone')
    expect(f.lists.brand).toEqual(['apple', 'samsung'])
    expect(f.flags['5g']).toBe(true)
    expect(f.single.price_max).toBe('300000')
    expect(f.page).toBe(3)
  })

  it('conserve les filtres à l’aller-retour', () => {
    const qs = 'q=dell&category=laptop&brand=dell,hp&ram_min=16&gpu_dedicated=1&page=2'
    const sorted = (s: string) => [...new URLSearchParams(s).entries()].sort().join('|')
    expect(sorted(roundTrip(qs))).toBe(sorted(qs))
  })

  it('ignore les paramètres inconnus et les pages invalides', () => {
    expect(roundTrip('foo=bar&page=abc')).toBe('')
    expect(parse('page=-4').page).toBe(1)
  })

  it('garde le filtre d’usage dans l’URL', () => {
    expect(parse('usage=gaming').single.usage).toBe('gaming')
    expect(roundTrip('category=laptop&usage=dev')).toContain('usage=dev')
  })

  it('garde le filtre de paiement sécurisé dans l’URL', () => {
    expect(parse('secure_payment=1').flags.secure_payment).toBe(true)
    expect(roundTrip('secure_payment=1')).toBe('secure_payment=1')
  })

  it('ne garde pas la page 1 dans l’URL', () => {
    expect(roundTrip('page=1')).toBe('')
  })

  it('revient à la page 1 quand un filtre change', () => {
    const f = withPage(parse('q=pc'), 4)
    expect(withSingle(f, 'city', 'cotonou').page).toBe(1)
    expect(withFlag(f, 'verified', true).page).toBe(1)
    expect(withList(f, 'grade', 'A', true).page).toBe(1)
  })

  it('ajoute et retire une valeur de liste', () => {
    let f = withList(parse(''), 'condition', 'used', true)
    f = withList(f, 'condition', 'new_sealed', true)
    expect(serializeFilters(f).get('condition')).toBe('used,new_sealed')
    f = withList(f, 'condition', 'used', false)
    expect(serializeFilters(f).get('condition')).toBe('new_sealed')
    f = withList(f, 'condition', 'new_sealed', false)
    expect(serializeFilters(f).has('condition')).toBe(false)
  })

  it('supprime une valeur vide et un drapeau désactivé', () => {
    let f = withSingle(parse('city=cotonou&verified=1'), 'city', '')
    f = withFlag(f, 'verified', false)
    expect(serializeFilters(f).toString()).toBe('')
  })

  it('compte les filtres actifs sans la recherche ni le tri', () => {
    expect(countActive(parse('q=pc&sort=recent&brand=dell,hp&5g=1&city=cotonou'))).toBe(3)
  })

  it('efface les filtres mais garde la recherche et le tri', () => {
    const f = clearFilters(parse('q=pc&sort=recent&brand=dell&5g=1&page=2'))
    expect(serializeFilters(f).toString()).toBe('q=pc&sort=recent')
  })
})
