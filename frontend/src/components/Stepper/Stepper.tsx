import { cx } from '@/lib/cx'
import styles from './Stepper.module.css'

type Props = { steps: string[]; current: number }

/** `current` is 1-based. Horizontal list on desktop, "Étape X sur N" plus a bar on mobile. */
export function Stepper({ steps, current }: Props) {
  return (
    <nav aria-label="Progression">
      <p className={styles.mobile}>
        Étape {current} sur {steps.length} : {steps[current - 1]}
      </p>
      <div
        className={styles.bar}
        role="progressbar"
        aria-valuemin={1}
        aria-valuemax={steps.length}
        aria-valuenow={current}
      >
        <span style={{ width: `${(current / steps.length) * 100}%` }} />
      </div>
      <ol className={styles.list}>
        {steps.map((s, i) => (
          <li
            key={s}
            className={cx(
              styles.step,
              i + 1 === current && styles.active,
              i + 1 < current && styles.done,
            )}
            aria-current={i + 1 === current ? 'step' : undefined}
          >
            <span className={styles.num}>{i + 1}</span>
            {s}
          </li>
        ))}
      </ol>
    </nav>
  )
}
