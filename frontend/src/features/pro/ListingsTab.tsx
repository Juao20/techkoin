import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Checkbox } from '@/components/Choice/Choice'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { api } from '@/lib/api'
import { formatFCFA, formatNumber } from '@/lib/format'
import { LoadState } from './shared'
import type { ShopStats } from './types'
import styles from './Pro.module.css'

export default function ListingsTab() {
  const { user } = useAuth()
  const pro = user?.shop?.plan === 'pro'
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [selected, setSelected] = useState<number[]>([])
  const { data, isPending, error, refetch } = useQuery({
    queryKey: ['shop', 'stats', 30],
    queryFn: () => api<ShopStats>('shop/stats/', { query: { period: 30 } }),
  })

  const change = useMutation({
    mutationFn: async ({ ids, verb }: { ids: number[]; verb: 'mark-sold' | 'archive' }) => {
      const results = await Promise.allSettled(
        ids.map((id) => api(`listings/${id}/${verb}/`, { method: 'POST' })),
      )
      return results.filter((r) => r.status === 'rejected').length
    },
    onSuccess: (failed, vars) => {
      setSelected([])
      void queryClient.invalidateQueries({ queryKey: ['shop', 'stats'] })
      void queryClient.invalidateQueries({ queryKey: ['me', 'listings'] })
      notify(
        failed
          ? `${failed} annonce(s) n’ont pas pu être modifiées.`
          : vars.verb === 'archive'
            ? 'Annonces archivées.'
            : 'Annonce marquée vendue.',
      )
    },
  })

  const state = <LoadState isPending={isPending} error={error} retry={() => void refetch()} />
  if (!data) return state
  if (data.listings.length === 0) {
    return (
      <EmptyState
        title="Aucune annonce en ligne"
        text="Publiez vos appareils pour suivre leurs vues et leurs contacts."
        action={<Link to="/vendre">Publier une annonce</Link>}
      />
    )
  }
  const all = data.listings.map((l) => l.id)
  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  return (
    <>
      <div className={styles.toolbar}>
        <Checkbox
          label={`Tout sélectionner (${all.length})`}
          checked={selected.length === all.length}
          onChange={(e) => setSelected(e.target.checked ? all : [])}
        />
        <div className={styles.actions}>
          <Button
            variant="secondary"
            disabled={selected.length === 0 || change.isPending}
            onClick={() => change.mutate({ ids: selected, verb: 'archive' })}
          >
            Archiver la sélection
          </Button>
          {pro && (
            <Button
              variant="secondary"
              disabled={selected.length === 0 || selected.length > 50}
              onClick={() =>
                navigate('/pro/analyse?module=optimisation', { state: { ids: selected } })
              }
            >
              Optimiser les textes ({selected.length})
            </Button>
          )}
        </div>
      </div>
      <p className={styles.hint}>Chiffres des 30 derniers jours.</p>
      <ul className={styles.rows}>
        {data.listings.map((l) => (
          <li key={l.id} className={styles.row}>
            <div className={styles.rowMain}>
              <Checkbox
                label=""
                aria-label={`Sélectionner ${l.title}`}
                checked={selected.includes(l.id)}
                onChange={() => toggle(l.id)}
              />
              <span className={styles.rowTitle}>
                <Link to={`/annonce/${l.slug}`}>{l.title}</Link>
              </span>
              <span className={styles.note}>
                {formatFCFA(l.price_fcfa)} · en ligne depuis {l.days_online} j{' '}
                {l.status === 'reserved' && <Tag tone="yellow">Réservée</Tag>}
              </span>
            </div>
            <dl className={styles.figures}>
              <div>
                <dt>Vues</dt>
                <dd>{formatNumber(l.views)}</dd>
              </div>
              <div>
                <dt>Contacts</dt>
                <dd>{formatNumber(l.contacts)}</dd>
              </div>
              <div>
                <dt>Favoris</dt>
                <dd>{formatNumber(l.favorites)}</dd>
              </div>
              <div>
                <dt>Taux de contact</dt>
                <dd>{String(l.contact_rate).replace('.', ',')} %</dd>
              </div>
            </dl>
            {l.status === 'active' && (
              <Button
                variant="ghost"
                disabled={change.isPending}
                onClick={() => change.mutate({ ids: [l.id], verb: 'mark-sold' })}
              >
                Marquer vendue
              </Button>
            )}
          </li>
        ))}
      </ul>
    </>
  )
}
