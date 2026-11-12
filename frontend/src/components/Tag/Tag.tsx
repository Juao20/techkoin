import type { ReactNode } from 'react'
import { cx } from '@/lib/cx'
import styles from './Tag.module.css'

export type TagTone = 'neutral' | 'green' | 'yellow' | 'red'

export function Tag({ tone = 'neutral', children }: { tone?: TagTone; children: ReactNode }) {
  return <span className={cx(styles.tag, styles[tone])}>{children}</span>
}
