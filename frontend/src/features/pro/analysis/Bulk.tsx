import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Checkbox } from '@/components/Choice/Choice'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { useToast } from '@/components/Toast/Toast'
import { ApiError, api } from '@/lib/api'
import { LoadState } from '../shared'
import type { BulkItem, ShopStats } from '../types'
import styles from '../Pro.module.css'

const MAX = 50

/** P6: new titles and descriptions for 1 to 50 listings, reviewed one by one before anything changes. */
export default function Bulk() {
  const location = useLocation()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const preselected = (location.state as { ids?: number[] } | null)?.ids ?? []
  const [chosen, setChosen] = useState<number[]>(preselected)
  const [items, setItems] = useState<BulkItem[] | null>(null)
  const [accepted, setAccepted] = useState<number[]>([])

  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['shop', 'stats', 30],
    queryFn: () => api<ShopStats>('shop/stats/', { query: { period: 30 } }),
  })
  const propose = useMutation({
    mutationFn: () =>
      api<{ items: BulkItem[] }>('insights/bulk-optimize/', {
        method: 'POST',
        body: { listing_ids: chosen },
      }),
    onSuccess: (res) => {
      setItems(res.items)
      setAccepted(res.items.map((i) => i.listing_id))
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Proposition impossible.'),
  })
  const apply = useMutation({
    mutationFn: () =>
      api<{ applied: number[] }>('insights/bulk-optimize/apply/', {
        method: 'POST',
        body: {
          items: (items ?? [])
            .filter((i) => accepted.includes(i.listing_id))
            .map((i) => ({ listing_id: i.listing_id, ...i.after })),
        },
      }),
    onSuccess: (res) => {
      notify(`${res.applied.length} annonce(s) mise(s) à jour.`)
      setItems(null)
      setChosen([])
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
      void queryClient.invalidateQueries({ queryKey: ['shop', 'stats'] })
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Modification impossible.'),
  })

  if (!data) return <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  const toggle = (list: number[], id: number) =>
    list.includes(id) ? list.filter((x) => x !== id) : [...list, id]

  return (
    <section className={styles.page} aria-labelledby="bulk-title">
      <div>
        <h2 id="bulk-title" className={styles.h2}>
          Optimisation en lot
        </h2>
        <p className={styles.hint}>
          Choisissez de 1 à {MAX} annonces. Vous voyez le texte actuel et le texte proposé, puis
          vous acceptez annonce par annonce. Rien ne change avant votre validation.
        </p>
      </div>

      {items === null ? (
        data.listings.length === 0 ? (
          <EmptyState
            title="Aucune annonce en ligne"
            text="Publiez des annonces pour les optimiser."
          />
        ) : (
          <>
            <div className={styles.toolbar}>
              <Checkbox
                label={`Tout sélectionner (${Math.min(data.listings.length, MAX)})`}
                checked={chosen.length === Math.min(data.listings.length, MAX)}
                onChange={(e) =>
                  setChosen(e.target.checked ? data.listings.slice(0, MAX).map((l) => l.id) : [])
                }
              />
              <Button
                disabled={chosen.length === 0 || chosen.length > MAX || propose.isPending}
                onClick={() => propose.mutate()}
              >
                {propose.isPending
                  ? 'Rédaction…'
                  : `Proposer de nouveaux textes (${chosen.length})`}
              </Button>
            </div>
            <ul className={styles.rows}>
              {data.listings.map((l) => (
                <li key={l.id} className={styles.row}>
                  <Checkbox
                    label={l.title}
                    checked={chosen.includes(l.id)}
                    onChange={() => setChosen((c) => toggle(c, l.id))}
                  />
                </li>
              ))}
            </ul>
          </>
        )
      ) : (
        <>
          <div className={styles.toolbar}>
            <Button
              disabled={accepted.length === 0 || apply.isPending}
              onClick={() => apply.mutate()}
            >
              {apply.isPending ? 'Application…' : `Appliquer ${accepted.length} modification(s)`}
            </Button>
            <Button variant="ghost" onClick={() => setAccepted(items.map((i) => i.listing_id))}>
              Tout accepter
            </Button>
            <Button variant="ghost" onClick={() => setAccepted([])}>
              Tout refuser
            </Button>
            <Button variant="ghost" onClick={() => setItems(null)}>
              Changer la sélection
            </Button>
          </div>
          <ul className={styles.rows}>
            {items.map((i) => (
              <li key={i.listing_id} className={styles.row}>
                <Checkbox
                  label="Appliquer cette modification"
                  checked={accepted.includes(i.listing_id)}
                  onChange={() => setAccepted((a) => toggle(a, i.listing_id))}
                />
                <div className={styles.compare}>
                  <div className={styles.before}>
                    <span className={styles.label}>Avant</span>
                    <p className={styles.text}>{i.before.title}</p>
                    <p className={styles.text}>{i.before.description || 'Pas de description.'}</p>
                  </div>
                  <div className={styles.after}>
                    <span className={styles.label}>Après</span>
                    <p className={styles.text}>{i.after.title}</p>
                    <p className={styles.text}>{i.after.description}</p>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}
