import type { InputHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { Field } from '../Field/Field'
import styles from '../Field/Field.module.css'
import { cx } from '@/lib/cx'

type Common = { label: string; hint?: string; error?: string }

export function Input({
  label,
  hint,
  error,
  className,
  ...rest
}: Common & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Field label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <input
          id={id}
          aria-describedby={describedBy}
          aria-invalid={invalid}
          className={cx(styles.control, className)}
          {...rest}
        />
      )}
    </Field>
  )
}

export function Textarea({
  label,
  hint,
  error,
  className,
  ...rest
}: Common & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <Field label={label} hint={hint} error={error}>
      {({ id, describedBy, invalid }) => (
        <textarea
          id={id}
          aria-describedby={describedBy}
          aria-invalid={invalid}
          className={cx(styles.control, styles.textarea, className)}
          {...rest}
        />
      )}
    </Field>
  )
}
