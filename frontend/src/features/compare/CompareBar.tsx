import { Link, useLocation } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { MAX_COMPARE, useCompare } from './CompareContext'
import styles from './CompareBar.module.css'

/** Fixed bar at the bottom of the screen while listings are selected for comparison. */
export function CompareBar() {
  const { ids, clear } = useCompare()
  const { pathname } = useLocation()
  if (ids.length === 0 || pathname === '/comparer') return null
  const ready = ids.length >= 2
  return (
    <>
      <div className={styles.spacer} aria-hidden />
      <div className={styles.bar} role="region" aria-label="Comparaison">
        <p className={styles.text}>
          {ids.length} annonce{ids.length > 1 ? 's' : ''} sur {MAX_COMPARE} à comparer
          {!ready && ' : choisissez-en une autre'}
        </p>
        <div className={styles.actions}>
          <Button variant="ghost" onClick={clear}>
            Vider
          </Button>
          {ready ? (
            <Link className={styles.go} to={`/comparer?ids=${ids.join(',')}`}>
              Comparer
            </Link>
          ) : (
            <Button disabled>Comparer</Button>
          )}
        </div>
      </div>
    </>
  )
}
