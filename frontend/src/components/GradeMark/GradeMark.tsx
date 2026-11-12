import styles from './GradeMark.module.css'

export type Grade = 'A' | 'B' | 'C'

const LABELS: Record<Grade, string> = {
  A: 'Comme neuf',
  B: 'Bon état',
  C: 'Traces visibles',
}

export function GradeMark({ grade }: { grade: Grade }) {
  return (
    <span className={styles.wrap}>
      <span className={styles.box} aria-hidden="true">
        {grade}
      </span>
      <span>
        <span className={styles.sr}>Note d'état {grade} : </span>
        {LABELS[grade]}
      </span>
    </span>
  )
}
