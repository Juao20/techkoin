import { describe, expect, it } from 'vitest'
import { formatFCFA, formatNumber } from './format'

describe('formatFCFA', () => {
  it('formats thousands with narrow no-break spaces', () => {
    expect(formatFCFA(185000)).toBe('185\u202f000\u202fFCFA')
  })

  it('leaves small amounts untouched', () => {
    expect(formatFCFA(500)).toBe('500\u202fFCFA')
    expect(formatFCFA(0)).toBe('0\u202fFCFA')
  })

  it('handles millions', () => {
    expect(formatNumber(1250000)).toBe('1\u202f250\u202f000')
  })

  it('rounds to whole francs', () => {
    expect(formatNumber(1999.6)).toBe('2\u202f000')
  })

  it('handles negative values', () => {
    expect(formatNumber(-12000)).toBe('-12\u202f000')
  })
})
