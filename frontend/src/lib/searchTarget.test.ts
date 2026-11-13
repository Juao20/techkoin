import { describe, expect, it } from 'vitest'
import { searchTarget } from './searchTarget'

describe('searchTarget', () => {
  it('envoie un mot ou un modèle vers la recherche simple', () => {
    expect(searchTarget('iphone 13')).toBe('/recherche?q=iphone%2013')
    expect(searchTarget('  ')).toBe('/recherche')
  })

  it('envoie une phrase vers la recherche intelligente', () => {
    expect(searchTarget('un pc pour coder pas cher')).toContain('/recherche?ia=')
  })

  it('reconnaît un budget même dans une courte demande', () => {
    expect(searchTarget('samsung max 250k')).toContain('?ia=')
    expect(searchTarget('pc 300000')).toContain('?ia=')
  })
})
