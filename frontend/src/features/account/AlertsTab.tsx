import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import styles from './AccountPage.module.css'

type Alert = {
  id: number
  name: string
  channel: 'email' | 'in_app' | 'whatsapp'
  is_active: boolean
  url: string
}

const CHANNELS = [
  { value: 'email', label: 'E-mail et notification' },
  { value: 'in_app', label: 'Notification seulement' },
  { value: 'whatsapp', label: 'WhatsApp (bientôt)' },
] as const

export function AlertsTab() {
  const queryClient = useQueryClient()
  const key = ['me', 'alerts']
  const { data, isPending } = useQuery({ queryKey: key, queryFn: () => api<Alert[]>('me/alerts/') })
  const refresh = () => void queryClient.invalidateQueries({ queryKey: key })
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api(`me/alerts/${id}/`, { method: 'PATCH', body }),
    onSuccess: refresh,
  })
  const remove = useMutation({
    mutationFn: (id: number) => api(`me/alerts/${id}/`, { method: 'DELETE' }),
    onSuccess: refresh,
  })

  if (isPending) return <p>Chargement…</p>
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="Aucune alerte"
        text="Lancez une recherche puis choisissez « Créer une alerte » : vous serez prévenu des nouvelles annonces."
        action={<Link to="/recherche">Rechercher un appareil</Link>}
      />
    )
  }
  return (
    <ul className={styles.orders}>
      {data.map((a) => (
        <li key={a.id} className={styles.alert}>
          <div className={styles.alertMain}>
            <Link to={a.url} className={styles.link}>
              {a.name}
            </Link>
            {!a.is_active && <Tag>En pause</Tag>}
          </div>
          <label className={styles.channel}>
            <span>Prévenir par</span>
            <select
              value={a.channel}
              onChange={(e) => patch.mutate({ id: a.id, body: { channel: e.target.value } })}
            >
              {CHANNELS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <div className={styles.itemActions}>
            <Button
              variant="secondary"
              onClick={() => patch.mutate({ id: a.id, body: { is_active: !a.is_active } })}
            >
              {a.is_active ? 'Mettre en pause' : 'Réactiver'}
            </Button>
            <Button variant="ghost" onClick={() => remove.mutate(a.id)}>
              Supprimer
            </Button>
          </div>
        </li>
      ))}
    </ul>
  )
}
