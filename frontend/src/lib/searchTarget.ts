/** Where a search box sends its text: plain search, or « Recherche intelligente » for sentences. */
export function searchTarget(text: string): string {
  const term = text.trim()
  if (!term) return '/recherche'
  const sentence = term.split(/\s+/).length >= 4 || /\d+\s?(k|mil|000)\b/i.test(term)
  return `/recherche?${sentence ? 'ia' : 'q'}=${encodeURIComponent(term)}`
}
