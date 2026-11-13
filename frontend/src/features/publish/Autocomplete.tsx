import { useQuery } from '@tanstack/react-query'
import { useId, useState } from 'react'
import { Field } from '@/components/Field/Field'
import fieldStyles from '@/components/Field/Field.module.css'
import { api } from '@/lib/api'
import { useDebounced } from '@/lib/useDebounced'
import styles from './Autocomplete.module.css'

type Props<T> = {
  label: string
  hint?: string
  error?: string
  path: string
  extraQuery?: Record<string, string | undefined>
  getLabel: (item: T) => string
  onPick: (item: T) => void
  initial?: string
  placeholder?: string
}

export function Autocomplete<T>({
  label,
  hint,
  error,
  path,
  extraQuery,
  getLabel,
  onPick,
  initial = '',
  placeholder,
}: Props<T>) {
  const listId = useId()
  const [text, setText] = useState(initial)
  const [open, setOpen] = useState(false)
  const q = useDebounced(text)
  const { data } = useQuery({
    queryKey: ['autocomplete', path, q, extraQuery],
    queryFn: () => api<T[]>(path, { query: { q, ...extraQuery } }),
    enabled: open,
    staleTime: 60_000,
  })

  return (
    <div className={styles.wrap}>
      <Field label={label} hint={hint} error={error}>
        {({ id, describedBy, invalid }) => (
          <input
            id={id}
            className={fieldStyles.control}
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            aria-autocomplete="list"
            aria-describedby={describedBy}
            aria-invalid={invalid}
            autoComplete="off"
            placeholder={placeholder}
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              setOpen(true)
            }}
            onFocus={() => setOpen(true)}
            onBlur={() => setTimeout(() => setOpen(false), 150)}
          />
        )}
      </Field>
      {/* Hide the list while the debounced query is behind the text: it would be stale. */}
      {open && q === text && data && data.length > 0 && (
        <ul id={listId} role="listbox" className={styles.list}>
          {data.map((item, i) => (
            <li key={i} role="option" aria-selected={false}>
              <button
                type="button"
                className={styles.option}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  setText(getLabel(item))
                  setOpen(false)
                  onPick(item)
                }}
              >
                {getLabel(item)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
