import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Brand, City, Page } from './types'

function unwrap<T>(data: T[] | Page<T>): T[] {
  return Array.isArray(data) ? data : data.results
}

export function useCities() {
  return useQuery({
    queryKey: ['cities'],
    queryFn: async () => unwrap(await api<City[] | Page<City>>('catalog/cities/')),
    staleTime: 60 * 60 * 1000,
  })
}

export function useBrands(category?: string) {
  return useQuery({
    queryKey: ['brands', category ?? ''],
    queryFn: async () =>
      unwrap(
        await api<Brand[] | Page<Brand>>('catalog/brands/', {
          query: { category },
        }),
      ),
    staleTime: 60 * 60 * 1000,
  })
}
