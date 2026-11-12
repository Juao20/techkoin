import { describe, expect, it } from 'vitest'
import { DEFAULT_ANSWERS, proposeGrade } from './grade'

const grade = (patch: Partial<typeof DEFAULT_ANSWERS>) =>
  proposeGrade({ ...DEFAULT_ANSWERS, ...patch }).grade

describe('note d’état proposée', () => {
  it('propose A quand rien n’est signalé', () => {
    expect(grade({})).toBe('A')
  })

  it('propose B pour de légères traces ou une batterie en baisse', () => {
    expect(grade({ screen: 'light' })).toBe('B')
    expect(grade({ body: 'light' })).toBe('B')
    expect(grade({ batteryWeak: true })).toBe('B')
  })

  it('propose C pour un écran fissuré, des traces visibles ou une panne', () => {
    expect(grade({ screenCracked: true })).toBe('C')
    expect(grade({ screen: 'visible' })).toBe('C')
    expect(grade({ body: 'visible' })).toBe('C')
    expect(grade({ fullyWorking: false })).toBe('C')
  })

  it('C l’emporte sur B et explique pourquoi', () => {
    const r = proposeGrade({ ...DEFAULT_ANSWERS, screen: 'light', screenCracked: true })
    expect(r.grade).toBe('C')
    expect(r.reasons).toContain('écran fissuré')
  })
})
