import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { Rows, SquaresFour } from '@phosphor-icons/react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { api } from '@/lib/api'
import { toCard } from '@/lib/listings'
import type { ListingCardApi, Page } from '@/lib/types'
import { useToast } from '@/components/Toast/Toast'
import { useCompare } from '@/features/compare/CompareContext'
import { CreateAlert } from './CreateAlert'
import { FilterPanel } from './FilterPanel'
import { SmartSearch } from './SmartSearch'
import {
  SORTS,
  parseFilters,
  serializeFilters,
  withPage,
  withSingle,
  type Filters,
} from './filters'
import styles from './SearchPage.module.css'

const PAGE_SIZE = 24

export default function SearchPage() {
  const [params, setParams] = useSearchParams()
  const compare = useCompare()
  const { notify } = useToast()
  const filters = useMemo(() => parseFilters(params), [params])
  const [panelOpen, setPanelOpen] = useState(false)
  const [view, setView] = useState<'grid' | 'list'>('grid')

  const apiParams = useMemo(() => serializeFilters(filters), [filters])
  const { data, isPending, isError, isPlaceholderData, refetch } = useQuery({
    queryKey: ['listings', apiParams.toString()],
    queryFn: () => api<Page<ListingCardApi>>('listings/', { query: Object.fromEntries(apiParams) }),
    placeholderData: keepPreviousData,
  })

  function update(next: Filters) {
    setParams(serializeFilters(next), { replace: true })
  }

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [filters.page])

  const totalPages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1
  const title = filters.single.q ? `Résultats pour « ${filters.single.q} »` : 'Toutes les annonces'

  return (
    <div className={styles.layout}>
      <aside className={styles.aside} data-open={panelOpen}>
        <FilterPanel filters={filters} onChange={update} />
        <div className={styles.apply}>
          <Button size="lg" onClick={() => setPanelOpen(false)}>
            Voir {data ? data.count : ''} résultat{data && data.count > 1 ? 's' : ''}
          </Button>
        </div>
      </aside>

      <section aria-labelledby="results-title" className={styles.results}>
        <SmartSearch
          initialQuery={params.get('ia') ?? ''}
          autoRun={Boolean(params.get('ia'))}
          onApply={(filters) => setParams(new URLSearchParams(filters), { replace: true })}
          onRemove={(keys) => {
            const next = new URLSearchParams(params)
            keys.forEach((k) => next.delete(k))
            next.delete('page')
            setParams(next, { replace: true })
          }}
        />
        <div className={styles.toolbar}>
          <div>
            <h1 id="results-title" className={styles.title}>
              {title}
            </h1>
            <p className={styles.count} aria-live="polite">
              {data ? `${data.count} annonce${data.count > 1 ? 's' : ''}` : ' '}
            </p>
            <CreateAlert params={params} />
          </div>
          <div className={styles.controls}>
            <Button
              variant="secondary"
              className={styles.filterToggle}
              onClick={() => setPanelOpen(true)}
            >
              Filtres
            </Button>
            <label className={styles.sort}>
              <span className={styles.sortLabel}>Trier par</span>
              <select
                aria-label="Trier par"
                className={styles.sortSelect}
                value={filters.single.sort ?? 'relevance'}
                onChange={(e) =>
                  update(
                    withSingle(
                      filters,
                      'sort',
                      e.target.value === 'relevance' ? '' : e.target.value,
                    ),
                  )
                }
              >
                {SORTS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <div className={styles.views} role="group" aria-label="Affichage">
              <button
                type="button"
                aria-pressed={view === 'grid'}
                aria-label="Affichage en grille"
                onClick={() => setView('grid')}
              >
                <SquaresFour size={20} />
              </button>
              <button
                type="button"
                aria-pressed={view === 'list'}
                aria-label="Affichage en liste"
                onClick={() => setView('list')}
              >
                <Rows size={20} />
              </button>
            </div>
          </div>
        </div>

        {isError ? (
          <EmptyState
            title="Les annonces ne se chargent pas"
            text="Vérifiez votre connexion puis réessayez."
            action={<Button onClick={() => void refetch()}>Réessayer</Button>}
          />
        ) : isPending ? (
          <p className={styles.loading}>Chargement des annonces…</p>
        ) : data.results.length === 0 ? (
          <EmptyState
            title="Aucune annonce ne correspond"
            text="Élargissez votre budget, retirez un filtre ou essayez une autre ville."
            action={
              <Link to="/recherche" className={styles.reset}>
                Effacer la recherche
              </Link>
            }
          />
        ) : (
          <>
            <h2 className={styles.srOnly}>Annonces</h2>
            <ul
              className={view === 'grid' ? styles.grid : styles.list}
              data-stale={isPlaceholderData}
            >
              {data.results.map((l, index) => (
                <li key={l.id}>
                  <ListingCard
                    priority={index < 4}
                    listing={toCard(l)}
                    compared={compare.has(l.id)}
                    onCompareChange={(checked) => {
                      if (!compare.toggle(l.id) && checked) {
                        notify('Vous pouvez comparer 3 annonces au maximum.')
                      }
                    }}
                  />
                </li>
              ))}
            </ul>
            {totalPages > 1 && (
              <nav className={styles.pager} aria-label="Pagination">
                <Button
                  variant="secondary"
                  disabled={filters.page <= 1}
                  onClick={() => update(withPage(filters, filters.page - 1))}
                >
                  Précédent
                </Button>
                <span>
                  Page {filters.page} sur {totalPages}
                </span>
                <Button
                  variant="secondary"
                  disabled={filters.page >= totalPages}
                  onClick={() => update(withPage(filters, filters.page + 1))}
                >
                  Suivant
                </Button>
              </nav>
            )}
          </>
        )}
      </section>
    </div>
  )
}
