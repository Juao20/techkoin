import styles from './ScoreBar.module.css'

export function ScoreBar({ label, score }: { label: string; score: number }) {
  const filled = Math.max(0, Math.min(10, Math.round(score)))
  return (
    <div className={styles.row}>
      <span className={styles.label}>{label}</span>
      <div
        className={styles.bar}
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={10}
        aria-valuenow={filled}
      >
        {Array.from({ length: 10 }, (_, i) => (
          <span key={i} className={i < filled ? styles.on : styles.off} />
        ))}
      </div>
      <span className={styles.value}>{filled}/10</span>
    </div>
  )
}
