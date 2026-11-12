/** Proposes a condition grade (A, B or C) from a short checklist answered by the seller. */

export type Wear = 'none' | 'light' | 'visible'

export type GradeAnswers = {
  screen: Wear // rayures sur l'écran
  body: Wear // rayures, chocs ou bosses sur le châssis
  screenCracked: boolean
  batteryWeak: boolean // la batterie tient moins bien qu'à l'achat
  fullyWorking: boolean // tout fonctionne : boutons, ports, caméras, réseau
}

export type Grade = 'A' | 'B' | 'C'

export const DEFAULT_ANSWERS: GradeAnswers = {
  screen: 'none',
  body: 'none',
  screenCracked: false,
  batteryWeak: false,
  fullyWorking: true,
}

export function proposeGrade(a: GradeAnswers): { grade: Grade; reasons: string[] } {
  const reasons: string[] = []
  if (a.screenCracked) reasons.push('écran fissuré')
  if (a.screen === 'visible') reasons.push('rayures visibles sur l’écran')
  if (a.body === 'visible') reasons.push('traces visibles sur le châssis')
  if (!a.fullyWorking) reasons.push('une fonction ne marche pas parfaitement')
  if (reasons.length > 0) return { grade: 'C', reasons }

  if (a.screen === 'light') reasons.push('micro-rayures sur l’écran')
  if (a.body === 'light') reasons.push('légères traces sur le châssis')
  if (a.batteryWeak) reasons.push('batterie en baisse')
  if (reasons.length > 0) return { grade: 'B', reasons }

  return { grade: 'A', reasons: ['aucun défaut signalé'] }
}
