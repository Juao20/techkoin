import { Link } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { ApiError } from '@/lib/api'
import styles from './Pro.module.css'
import type { Period, Preview } from './types'

export const dateFr = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium' })

export function PeriodPicker<T extends number>({
  value,
  options,
  onChange,
}: {
  value: T
  options: readonly T[]
  onChange: (p: T) => void
}) {
  return (
    <div className={styles.segment} role="group" aria-label="Période">
      {options.map((p) => (
        <button key={p} type="button" aria-pressed={value === p} onClick={() => onChange(p)}>
          {p} jours
        </button>
      ))}
    </div>
  )
}

export const PERIODS: readonly Period[] = [7, 30, 90]

/** « +12 % » / « -5 % » against the previous period, or nothing when there is no base. */
export function Change({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) return null
  const sign = value > 0 ? '+' : ''
  return (
    <span className={value > 0 ? styles.up : value < 0 ? styles.down : undefined}>
      {sign}
      {value} %
    </span>
  )
}

export function LoadState({
  isPending,
  error,
  retry,
}: {
  isPending: boolean
  error: unknown
  retry: () => void
}) {
  if (isPending) return <p>Chargement…</p>
  if (error) {
    return (
      <EmptyState
        title="Chargement impossible"
        text={error instanceof ApiError ? error.message : 'Une erreur est survenue.'}
        action={<Button onClick={retry}>Réessayer</Button>}
      />
    )
  }
  return null
}

/** Free plan: the first element is real, the rest is announced, and the offer is one click away. */
export function PreviewNotice({ meta, what }: { meta: Preview; what: string }) {
  if (!meta.preview) return null
  return (
    <aside className={styles.offer} aria-label="Aperçu de l’offre Pro">
      <p>
        <strong>Aperçu :</strong>{' '}
        {meta.hidden > 0
          ? `1 ${what} affiché sur ${meta.total}. ${meta.hidden} de plus avec l’offre Pro.`
          : `Voici le premier ${what}. L’offre Pro affiche le détail complet.`}
      </p>
      <Link to="/pro/abonnement" className={styles.offerLink}>
        Découvrir l’offre Pro
      </Link>
    </aside>
  )
}

export function ProOnly({ title, text }: { title: string; text: string }) {
  return (
    <div className={styles.offer} role="note">
      <h3 className={styles.h2}>{title}</h3>
      <p>{text}</p>
      <p>Cette fonction fait partie de l’offre Pro.</p>
      <Link to="/pro/abonnement" className={styles.offerLink}>
        Découvrir l’offre Pro
      </Link>
    </div>
  )
}

/** The server said 403 (plan ended since the page loaded): same message as a Free shop. */
export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403
}
