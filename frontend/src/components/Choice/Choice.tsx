import type { InputHTMLAttributes } from 'react'
import styles from './Choice.module.css'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string }

export function Checkbox({ label, ...rest }: Props) {
  return (
    <label className={styles.choice}>
      <input type="checkbox" className={styles.box} {...rest} />
      <span>{label}</span>
    </label>
  )
}

export function Radio({ label, ...rest }: Props) {
  return (
    <label className={styles.choice}>
      <input type="radio" className={styles.radio} {...rest} />
      <span>{label}</span>
    </label>
  )
}
