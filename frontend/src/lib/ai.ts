import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { ListingCardApi } from './types'

export type AiStatus = { model_available: boolean; voice_available: boolean }

export function useAiStatus() {
  return useQuery({
    queryKey: ['ai-status'],
    queryFn: () => api<AiStatus>('ai/status/'),
    staleTime: 10 * 60 * 1000,
  })
}

export type SearchChip = { keys: string[]; label: string }
export type SearchInterpretation = {
  query: string
  filters: Record<string, string>
  chips: SearchChip[]
  confidence: number
  used_ai: boolean
}

export type AssistantAnswer = {
  answer: string
  information_missing: boolean
  suggested_seller_question: string | null
  used_ai: boolean
}

export type CompareRowApi = {
  key: string
  label: string
  values: Array<string | number | null>
  best: number | null
  group: 'spec' | 'price' | 'usage' | 'trust'
}

export type CompareVerdict = {
  winner_listing_id: number
  summary: string
  reasons: string[]
  warnings: string[]
  per_listing: Array<{ listing_id: number; best_for: string; verdict_line: string }>
}

export type ComparePayload = {
  rows: CompareRowApi[]
  verdict: CompareVerdict
  used_ai: boolean
  usage: string | null
  budget: number | null
  listings: ListingCardApi[]
}

export type VoiceResult =
  | { available: false; used_ai: false }
  | {
      available: true
      transcript: string
      used_ai: boolean
      fields: {
        model_text: string | null
        category: string | null
        storage_gb: number | null
        ram_gb: number | null
        battery_health_pct: number | null
        condition_type: string | null
        grade: string | null
        accessories: string[]
        color: string | null
        price_fcfa: number | null
        defects: string | null
      }
      device_model: { slug: string; label: string; category: string } | null
    }

export const AUTO_NOTICE = 'Réponse générée automatiquement, vérifiez les informations clés.'
