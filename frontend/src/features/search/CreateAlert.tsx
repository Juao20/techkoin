import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Bell } from '@phosphor-icons/react'
import { Link, useLocation } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import styles from './SearchPage.module.css'

/** « Créer une alerte pour cette recherche »: the current filters, saved as they are in the URL. */
export function CreateAlert({ params }: { params: URLSearchParams }) {
  const { user } = useAuth()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const filters = Object.fromEntries(params)
  const hasCriteria = [...params.keys()].some((k) => k !== 'page' && k !== 'sort')

  const create = useMutation({
    mutationFn: () => api('me/alerts/', { method: 'POST', body: { filters } }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['me', 'alerts'] })
      notify('Alerte créée. Vous serez prévenu des nouvelles annonces.')
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Création impossible.'),
  })

  if (!hasCriteria) return null
  if (!user) {
    return (
      <Link
        to="/connexion"
        state={{ from: location.pathname + location.search }}
        className={styles.alertLink}
      >
        <Bell size={18} aria-hidden /> Connectez-vous pour créer une alerte
      </Link>
    )
  }
  return (
    <Button
      variant="secondary"
      className={styles.alertButton}
      disabled={create.isPending}
      onClick={() => create.mutate()}
    >
      <Bell size={18} aria-hidden /> Créer une alerte pour cette recherche
    </Button>
  )
}
