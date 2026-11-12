import type { ReactNode } from 'react'
import { cx } from '@/lib/cx'
import styles from './CompareTable.module.css'

export type CompareColumn = { id: string; title: string }
export type CompareRow = { label: string; values: ReactNode[]; bestIndex?: number }

export function CompareTable({ columns, rows }: { columns: CompareColumn[]; rows: CompareRow[] }) {
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <td className={styles.corner} />
            {columns.map((c) => (
              <th key={c.id} scope="col" className={styles.head}>
                {c.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label}>
              <th scope="row" className={styles.label}>
                {r.label}
              </th>
              {r.values.map((v, i) => (
                <td key={i} className={cx(styles.cell, r.bestIndex === i && styles.best)}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
