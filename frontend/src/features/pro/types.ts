// Shapes of the shop dashboard API (spec 13, « Boutique » and « Pro »).

export type Period = 7 | 30 | 90

export type Totals = {
  views: number
  contacts: number
  favorites: number
  sales: number
  revenue_fcfa: number
  contact_rate: number
  change: Record<'views' | 'contacts' | 'favorites' | 'sales' | 'revenue_fcfa', number | null>
}

export type ListingRow = {
  id: number
  slug: string
  title: string
  category: string
  status: string
  price_fcfa: number
  city: string
  days_online: number
  views: number
  contacts: number
  favorites: number
  contact_rate: number
}

export type ShopStats = {
  period: Period
  totals: Totals
  series: Array<{ date: string; views: number; contacts: number }>
  listings: ListingRow[]
  active_listings: number
}

/** Free shops get the first element of each module and a count of what stays hidden. */
export type Preview = { preview: boolean; total: number; hidden: number }

export type DemandRow = {
  category: string
  label: string
  budget_max: number | null
  budget_label: string
  city: string | null
  searches: number
  no_result: number
  supply: number
  my_supply: number
  median_budget_fcfa: number | null
  previous_searches: number
  change_pct: number | null
  searches_per_listing: number
}
export type Demand = Preview & {
  period: number
  min_searches: number
  rows: DemandRow[]
  recommendations?: string[]
  used_ai?: boolean
}

export type PricingRow = {
  id: number
  slug: string
  title: string
  price_fcfa: number
  estimate_fcfa: number | null
  estimate_low_fcfa: number | null
  estimate_high_fcfa: number | null
  estimate_sample_size: number
  days_online: number
  views: number
  contacts: number
  category_avg_views: number
  category_avg_contacts: number
  action: 'lower' | 'raise' | 'keep' | 'none'
  advised_price_fcfa: number | null
  gap_pct: number | null
  indicative: boolean
  note: string
}
export type Pricing = Preview & { rows: PricingRow[]; used_ai: boolean }

export type DormantRow = {
  id: number
  slug: string
  title: string
  price_fcfa: number
  days_online: number
  views: number
  contacts: number
  contact_rate: number
  median_contact_rate: number
  causes: Array<{ code: string; label: string; detail: string }>
  advised_price_fcfa: number | null
  note: string
  fix: { title: string; description: string; used_ai: boolean } | null
}
export type Dormant = Preview & { min_days: number; rows: DormantRow[]; used_ai: boolean }

export type ReportSummary = {
  id: number
  period_start: string
  period_end: string
  summary: string
  emailed_at: string | null
}
export type Report = ReportSummary & {
  actions: string[]
  used_ai: boolean
  figures: {
    views: number
    contacts: number
    favorites: number
    sales: number
    revenue_fcfa: number
    change: Record<'views' | 'contacts' | 'sales', number | null>
    best_listings: Array<{ title: string; views: number; contacts: number }>
    listings_to_reprice: number
    dormant_listings: number
    unmet_demand: Array<{ label: string; searches: number; city: string | null }>
  }
}

export type ChatAnswer = {
  answer: string
  used_ai: boolean
  calls: Array<{ name: string; arguments: Record<string, unknown> }>
}

export type BulkItem = {
  listing_id: number
  slug: string
  before: { title: string; description: string }
  after: { title: string; description: string }
  highlights: string[]
  used_ai: boolean
}

export type CompetitorFacts = {
  id: number
  titre: string
  prix_fcfa: number
  ecart_estimation_pct: number | null
  badge_prix: string | null
  garantie_mois: number
  accessoires: string[]
  photos: number
  slug?: string
  city?: string
  shop?: string | null
}
export type Competition = {
  listing_id: number
  mine?: CompetitorFacts
  competitors: CompetitorFacts[]
  why_them: string
  actions: Array<{ kind: string; text: string }>
  used_ai: boolean
  note?: string
}

export type SubscriptionRow = {
  id: number
  status: 'pending' | 'active' | 'failed' | 'expired'
  status_label: string
  amount_fcfa: number
  starts_at: string | null
  ends_at: string | null
  created_at: string
  checkout_url: string
}
export type SubscriptionState = {
  plan: 'free' | 'pro'
  plan_expires_at: string | null
  price_fcfa: number
  latest: SubscriptionRow | null
  history: SubscriptionRow[]
}
