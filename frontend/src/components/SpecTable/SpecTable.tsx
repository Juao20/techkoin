import styles from './SpecTable.module.css'

export type SpecGroup = { title: string; rows: Array<{ label: string; value: string }> }

export function SpecTable({ groups }: { groups: SpecGroup[] }) {
  return (
    <div className={styles.wrap}>
      {groups.map((g) => (
        <table key={g.title} className={styles.table}>
          <caption className={styles.caption}>{g.title}</caption>
          <tbody>
            {g.rows.map((r) => (
              <tr key={r.label}>
                <th scope="row" className={styles.label}>
                  {r.label}
                </th>
                <td className={styles.value}>{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ))}
    </div>
  )
}
