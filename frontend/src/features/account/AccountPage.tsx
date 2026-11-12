import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Input } from '@/components/Input/Input'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { Tabs } from '@/components/Tabs/Tabs'
import { Tag, type TagTone } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import { toCard } from '@/lib/listings'
import type { ListingCardApi, User } from '@/lib/types'
import { VerificationTab } from './VerificationTab'
import styles from './AccountPage.module.css'

const STATUS: Record<string, { label: string; tone: TagTone }> = {
  draft: { label: 'Brouillon', tone: 'neutral' },
  pending_review: { label: 'En relecture', tone: 'yellow' },
  active: { label: 'En ligne', tone: 'green' },
  reserved: { label: 'Réservée', tone: 'yellow' },
  sold: { label: 'Vendue', tone: 'neutral' },
  rejected: { label: 'Refusée', tone: 'red' },
  archived: { label: 'Archivée', tone: 'neutral' },
}

function MyListings() {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const { data, isPending } = useQuery({
    queryKey: ['me', 'listings'],
    queryFn: () => api<ListingCardApi[]>('me/listings/'),
  })
  const action = useMutation({
    mutationFn: ({ id, verb }: { id: number; verb: 'mark-sold' | 'archive' }) =>
      api(`listings/${id}/${verb}/`, { method: 'POST' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['me', 'listings'] }),
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Action impossible.'),
  })

  if (isPending) return <p>Chargement…</p>
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="Vous n’avez pas encore d’annonce"
        text="Publiez votre premier appareil en quelques minutes."
        action={<Link to="/vendre">Vendre un appareil</Link>}
      />
    )
  }
  return (
    <ul className={styles.list}>
      {data.map((l) => {
        const st = STATUS[l.status] ?? { label: l.status, tone: 'neutral' as TagTone }
        const live = l.status === 'active' || l.status === 'reserved'
        return (
          <li key={l.id} className={styles.item}>
            <ListingCard listing={toCard(l)} />
            <div className={styles.itemActions}>
              <Tag tone={st.tone}>{st.label}</Tag>
              {l.rejection_reason && <p className={styles.reason}>{l.rejection_reason}</p>}
              {l.status === 'draft' && (
                <Link to={`/vendre/${l.id}`} className={styles.link}>
                  Reprendre
                </Link>
              )}
              {live && (
                <>
                  <Button
                    variant="secondary"
                    disabled={action.isPending}
                    onClick={() => action.mutate({ id: l.id, verb: 'mark-sold' })}
                  >
                    Marquer vendue
                  </Button>
                  <Button
                    variant="ghost"
                    disabled={action.isPending}
                    onClick={() => action.mutate({ id: l.id, verb: 'archive' })}
                  >
                    Archiver
                  </Button>
                </>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}

function Favorites() {
  const { data, isPending } = useQuery({
    queryKey: ['me', 'favorites'],
    queryFn: () => api<ListingCardApi[]>('me/favorites/'),
  })
  if (isPending) return <p>Chargement…</p>
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="Aucun favori"
        text="Touchez le cœur sur une annonce pour la retrouver ici."
        action={<Link to="/recherche">Parcourir les annonces</Link>}
      />
    )
  }
  return (
    <ul className={styles.grid}>
      {data.map((l) => (
        <li key={l.id}>
          <ListingCard listing={toCard(l)} />
        </li>
      ))}
    </ul>
  )
}

function Profile({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [form, setForm] = useState({
    first_name: user.first_name,
    last_name: user.last_name,
    phone: user.phone,
    whatsapp_number: user.whatsapp_number,
    city: user.city,
    quartier: user.quartier,
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      const res = await api<{ user: User }>('me/', { method: 'PATCH', body: form })
      queryClient.setQueryData(['me'], { user: res.user })
      notify('Profil enregistré.')
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fields)
      notify(err instanceof ApiError ? err.message : 'Enregistrement impossible.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <Input
        label="Prénom"
        value={form.first_name}
        onChange={set('first_name')}
        error={errors.first_name}
      />
      <Input
        label="Nom"
        value={form.last_name}
        onChange={set('last_name')}
        error={errors.last_name}
      />
      <Input
        label="Téléphone"
        type="tel"
        value={form.phone}
        onChange={set('phone')}
        error={errors.phone}
      />
      <Input
        label="Numéro WhatsApp"
        type="tel"
        hint="Utilisé quand un acheteur vous écrit depuis une annonce."
        value={form.whatsapp_number}
        onChange={set('whatsapp_number')}
        error={errors.whatsapp_number}
      />
      <Input label="Ville" value={form.city} onChange={set('city')} error={errors.city} />
      <Input
        label="Quartier"
        value={form.quartier}
        onChange={set('quartier')}
        error={errors.quartier}
      />
      <Button type="submit" size="lg" disabled={busy}>
        {busy ? 'Enregistrement…' : 'Enregistrer'}
      </Button>
    </form>
  )
}

export default function AccountPage() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  if (loading) return <p>Chargement…</p>
  if (!user) return <Navigate to="/connexion" replace state={{ from: '/compte' }} />

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Bonjour {user.first_name}</h1>
          <p className={styles.meta}>
            {user.account_type === 'boutique' && user.shop ? (
              <>
                Boutique <Link to={`/boutique/${user.shop.slug}`}>{user.shop.name}</Link>
              </>
            ) : (
              user.email
            )}
          </p>
        </div>
        <div className={styles.headerActions}>
          <Link to="/vendre" className={styles.sell}>
            Vendre un appareil
          </Link>
          <Button
            variant="secondary"
            onClick={async () => {
              await logout()
              navigate('/', { replace: true })
            }}
          >
            Se déconnecter
          </Button>
        </div>
      </header>
      <Tabs
        items={[
          { value: 'listings', label: 'Mes annonces', content: <MyListings /> },
          { value: 'favorites', label: 'Favoris', content: <Favorites /> },
          { value: 'profile', label: 'Profil', content: <Profile user={user} /> },
          {
            value: 'verification',
            label: 'Vérification',
            content: <VerificationTab user={user} />,
          },
        ]}
      />
    </div>
  )
}
