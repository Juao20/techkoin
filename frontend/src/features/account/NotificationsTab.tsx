import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { api } from '@/lib/api'
import styles from './AccountPage.module.css'

type Notifications = {
  unread: number
  results: Array<{
    id: number
    title: string
    body: string
    url: string
    read: boolean
    created_at: string
  }>
}

const DATE = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
export const NOTIFICATIONS_KEY = ['me', 'notifications']

export function useUnreadCount(enabled: boolean) {
  const { data } = useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: () => api<Notifications>('me/notifications/'),
    enabled,
  })
  return data?.unread ?? 0
}

export function NotificationsTab() {
  const queryClient = useQueryClient()
  const { data, isPending } = useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: () => api<Notifications>('me/notifications/'),
  })
  const markRead = useMutation({
    mutationFn: () => api('me/notifications/', { method: 'POST' }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY }),
  })
  const unread = data?.unread ?? 0
  const { mutate } = markRead
  // Opening the tab is reading it; the unread marks stay visible until the list is closed.
  useEffect(() => {
    if (unread > 0) {
      const t = setTimeout(() => mutate(), 3000)
      return () => clearTimeout(t)
    }
  }, [unread, mutate])

  if (isPending) return <p>Chargement…</p>
  if (!data || data.results.length === 0) {
    return (
      <EmptyState
        title="Aucune notification"
        text="Les nouvelles annonces qui correspondent à vos alertes apparaîtront ici."
        action={<Link to="/recherche">Rechercher un appareil</Link>}
      />
    )
  }
  return (
    <ul className={styles.orders}>
      {data.results.map((n) => (
        <li key={n.id} className={styles.notification} data-unread={!n.read}>
          <Link to={n.url || '/recherche'} className={styles.link}>
            {n.title}
          </Link>
          <p className={styles.orderMeta}>{n.body}</p>
          <p className={styles.orderMeta}>{DATE.format(new Date(n.created_at))}</p>
        </li>
      ))}
    </ul>
  )
}
