/** Search filters live in the URL: this module is the only place that knows their names. */

export const SORTS = [
  { value: 'relevance', label: 'Pertinence' },
  { value: 'recent', label: 'Plus récentes' },
  { value: 'price_asc', label: 'Prix croissant' },
  { value: 'price_desc', label: 'Prix décroissant' },
  { value: 'best_deal', label: 'Meilleures affaires' },
] as const

/** Params that hold a single value. */
const SINGLE = [
  'q',
  'category',
  'price_min',
  'price_max',
  'city',
  'ram_min',
  'storage_min',
  'storage_type',
  'os',
  'screen_min',
  'screen_max',
  'cpu_family',
  'cpu_gen_min',
  'battery_min',
  'keyboard',
  'seller_type',
  'warranty',
  'sort',
] as const

/** Params that hold a comma separated list of values. */
const LISTS = ['brand', 'condition', 'grade'] as const

/** Params that are either present (true) or absent. */
const FLAGS = [
  'gpu_dedicated',
  '5g',
  'dual_sim',
  'unlocked',
  'no_replaced_parts',
  'cellular',
  'stylus',
  'verified',
  'invoice',
] as const

export type SingleKey = (typeof SINGLE)[number]
export type ListKey = (typeof LISTS)[number]
export type FlagKey = (typeof FLAGS)[number]

export type Filters = {
  single: Partial<Record<SingleKey, string>>
  lists: Partial<Record<ListKey, string[]>>
  flags: Partial<Record<FlagKey, boolean>>
  page: number
}

export function parseFilters(params: URLSearchParams): Filters {
  const filters: Filters = { single: {}, lists: {}, flags: {}, page: 1 }
  for (const key of SINGLE) {
    const value = params.get(key)
    if (value) filters.single[key] = value
  }
  for (const key of LISTS) {
    const value = params.get(key)
    if (value) filters.lists[key] = value.split(',').filter(Boolean)
  }
  for (const key of FLAGS) {
    if (params.get(key) === '1') filters.flags[key] = true
  }
  const page = Number(params.get('page'))
  if (Number.isInteger(page) && page > 1) filters.page = page
  return filters
}

export function serializeFilters(filters: Filters): URLSearchParams {
  const params = new URLSearchParams()
  for (const key of SINGLE) {
    const value = filters.single[key]
    if (value) params.set(key, value)
  }
  for (const key of LISTS) {
    const value = filters.lists[key]
    if (value && value.length > 0) params.set(key, value.join(','))
  }
  for (const key of FLAGS) {
    if (filters.flags[key]) params.set(key, '1')
  }
  if (filters.page > 1) params.set('page', String(filters.page))
  return params
}

/** Any filter change sends the user back to page 1. */
export function withSingle(filters: Filters, key: SingleKey, value: string): Filters {
  const single = { ...filters.single }
  if (value) single[key] = value
  else delete single[key]
  return { ...filters, single, page: 1 }
}

export function withList(filters: Filters, key: ListKey, value: string, on: boolean): Filters {
  const current = filters.lists[key] ?? []
  const next = on ? [...new Set([...current, value])] : current.filter((v) => v !== value)
  return { ...filters, lists: { ...filters.lists, [key]: next }, page: 1 }
}

export function withFlag(filters: Filters, key: FlagKey, on: boolean): Filters {
  const flags = { ...filters.flags }
  if (on) flags[key] = true
  else delete flags[key]
  return { ...filters, flags, page: 1 }
}

export function withPage(filters: Filters, page: number): Filters {
  return { ...filters, page }
}

export function countActive(filters: Filters): number {
  const single = Object.keys(filters.single).filter((k) => k !== 'sort' && k !== 'q').length
  const lists = Object.values(filters.lists).filter((v) => v && v.length > 0).length
  return single + lists + Object.keys(filters.flags).length
}

export function clearFilters(filters: Filters): Filters {
  const keep: Filters['single'] = {}
  if (filters.single.q) keep.q = filters.single.q
  if (filters.single.sort) keep.sort = filters.single.sort
  return { single: keep, lists: {}, flags: {}, page: 1 }
}
