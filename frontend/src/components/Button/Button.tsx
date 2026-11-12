import type { ButtonHTMLAttributes } from 'react'
import { cx } from '@/lib/cx'
import styles from './Button.module.css'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: 'md' | 'lg'
}

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  type = 'button',
  ...rest
}: Props) {
  return (
    <button
      type={type}
      className={cx(styles.button, styles[variant], size === 'lg' && styles.lg, className)}
      {...rest}
    />
  )
}
