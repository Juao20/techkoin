import styles from './TestBanner.module.css'

/** Shown on every page of the payment journey (spec 9.1). */
export function TestBanner() {
  return (
    <p className={styles.banner} role="note">
      <strong>Mode test</strong> : aucun argent réel n’est débité.
    </p>
  )
}
