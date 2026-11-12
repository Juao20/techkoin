import type { ListingCardData } from '@/components/ListingCard/ListingCard'
import type { ListingCardApi } from './types'

export function timeAgo(iso: string | null, now = new Date()): string {
  if (!iso) return ''
  const diffMin = Math.max(0, Math.round((now.getTime() - new Date(iso).getTime()) / 60000))
  if (diffMin < 60) return diffMin <= 1 ? "à l'instant" : `il y a ${diffMin} min`
  const hours = Math.round(diffMin / 60)
  if (hours < 24) return `il y a ${hours} h`
  const days = Math.round(hours / 24)
  if (days < 30) return days === 1 ? 'hier' : `il y a ${days} jours`
  const months = Math.round(days / 30)
  return `il y a ${months} mois`
}

export const CONDITION_LABELS: Record<string, string> = {
  new_sealed: 'Neuf scellé',
  new_open: 'Neuf ouvert',
  used: 'Occasion',
  refurbished: 'Reconditionné',
}

export const CATEGORY_LABELS: Record<string, string> = {
  smartphone: 'Smartphones',
  tablet: 'Tablettes',
  laptop: 'PC portables',
  desktop: 'PC fixes',
}

export function toCard(l: ListingCardApi): ListingCardData {
  return {
    id: String(l.id),
    href: `/annonce/${l.slug}`,
    title: l.title,
    specs: l.specs,
    priceFcfa: l.price_fcfa,
    priceBadge: l.price_badge && l.price_badge !== 'unknown' ? l.price_badge : undefined,
    city: l.city,
    age: timeAgo(l.published_at),
    grade: l.grade || undefined,
    imageUrl: l.thumb ?? undefined,
    keyboard: l.keyboard_layout ? l.keyboard_layout.toUpperCase() : undefined,
    verifiedSeller: l.seller_verified && Boolean(l.shop_name),
  }
}
