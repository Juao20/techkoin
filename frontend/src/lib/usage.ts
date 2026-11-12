export const USAGE_LABELS: Record<string, string> = {
  office: 'Bureautique',
  study: 'Études',
  dev: 'Développement',
  gaming: 'Jeux',
  creative: 'Photo et vidéo',
  battery: 'Autonomie',
  everyday: 'Quotidien',
  photo: 'Photo',
  business: 'Professionnel',
}

export const PC_USAGES = ['office', 'study', 'dev', 'gaming', 'creative', 'battery']
export const MOBILE_USAGES = ['everyday', 'photo', 'gaming', 'battery', 'business']

export const BADGES = {
  good_deal: { tone: 'yellow', label: 'Bonne affaire' },
  fair: { tone: 'green', label: 'Prix correct' },
  above_market: { tone: 'red', label: 'Au-dessus du marché' },
} as const
