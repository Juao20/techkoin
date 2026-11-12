const NARROW_NBSP = '\u202f'

/** Formats an integer with narrow no-break spaces as thousands separator: 185 000 */
export function formatNumber(value: number): string {
  const rounded = Math.round(value)
  const sign = rounded < 0 ? '-' : ''
  const digits = String(Math.abs(rounded))
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, NARROW_NBSP)
}

/** The single price formatter: 185 000 FCFA (narrow no-break space before the currency too). */
export function formatFCFA(value: number): string {
  return `${formatNumber(value)}${NARROW_NBSP}FCFA`
}
