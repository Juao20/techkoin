import type { ReactNode } from 'react'
import styles from './EmptyState.module.css'

type Props = { title: string; text: string; action?: ReactNode }

export function EmptyState({ title, text, action }: Props) {
  return (
    <div className={styles.wrap}>
      <h3>{title}</h3>
      <p className={styles.text}>{text}</p>
      {action}
    </div>
  )
}
