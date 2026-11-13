export type Category = 'smartphone' | 'tablet' | 'laptop' | 'desktop'

export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] }

export type Shop = {
  name: string
  slug: string
  logo: string | null
  description: string
  address: string
  city: string
  quartier: string
  opening_hours: string
  whatsapp_number: string
  is_verified: boolean
  verification_status: 'none' | 'pending' | 'verified' | 'rejected'
  plan: string
}

export type User = {
  id: number
  email: string
  phone: string
  whatsapp_number: string
  first_name: string
  last_name: string
  account_type: 'particulier' | 'boutique'
  city: string
  quartier: string
  identity_status: string
  is_moderator: boolean
  shop: Shop | null
}

export type ListingCardApi = {
  id: number
  slug: string
  title: string
  category: Category
  brand: string
  price_fcfa: number
  negotiable: boolean
  price_badge: '' | 'unknown' | 'good_deal' | 'fair' | 'above_market' | null
  condition_type: string
  grade: '' | 'A' | 'B' | 'C'
  city: string
  specs: string
  thumb: string | null
  keyboard_layout: string
  warranty_months: number
  has_invoice: boolean
  seller_verified: boolean
  shop_name: string | null
  published_at: string | null
  status: string
  favorited: boolean
  rejection_reason: string
  accepts_secure_payment: boolean
}

export type Photo = { id: number; image: string; thumb: string; kind: string; position: number }

export type Seller = {
  type: 'shop' | 'individual'
  name: string
  slug: string | null
  verified: boolean
  city: string
  member_since: string
}

export type ListingDetailApi = ListingCardApi & {
  photos: Photo[]
  seller: Seller
  description: string
  quartier: string
  accessories: string[]
  provenance: string
  model_slug: string | null
  has_imei: boolean
  ram_gb: number | null
  storage_gb: number | null
  storage_type: string
  color: string
  screen_size_in: string | number | null
  screen_resolution: string
  refresh_rate_hz: number | null
  processor: { name: string; family: string; generation: number | null } | null
  gpu: string | null
  gpu_dedicated: boolean
  vram_gb: number | null
  touchscreen: boolean
  os: string
  keyboard_backlit: boolean
  battery_cycles: number | null
  battery_autonomy_h: number | null
  ports: string[]
  ram_upgradable: boolean
  battery_health_pct: number | null
  network_5g: boolean
  dual_sim: boolean
  esim: boolean
  carrier_unlocked: boolean
  account_removed: boolean
  biometrics_ok: boolean
  screen_original: boolean
  replaced_parts: string[]
  cellular: boolean
  stylus_included: boolean
  keyboard_included: boolean
  estimate_low: number | null
  estimate_mid: number | null
  estimate_high: number | null
  usage_scores: Record<string, number>
  advised_usage: string | null
  estimate_indicative: boolean
  views_count: number
  favorites_count: number
}

export type City = { slug: string; name: string }
export type Brand = { slug: string; name: string }
