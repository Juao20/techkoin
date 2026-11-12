import * as RadixSelect from '@radix-ui/react-select'
import { CaretDown, Check } from '@phosphor-icons/react'
import { useId } from 'react'
import styles from './Select.module.css'

export type SelectOption = { value: string; label: string }

type Props = {
  label: string
  options: SelectOption[]
  value?: string
  onValueChange?: (value: string) => void
  placeholder?: string
  error?: string
}

export function Select({ label, options, value, onValueChange, placeholder, error }: Props) {
  const id = useId()
  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
      </label>
      <RadixSelect.Root value={value} onValueChange={onValueChange}>
        <RadixSelect.Trigger id={id} className={styles.trigger} aria-invalid={Boolean(error)}>
          <RadixSelect.Value placeholder={placeholder ?? 'Choisir'} />
          <RadixSelect.Icon>
            <CaretDown size={18} />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>
        <RadixSelect.Portal>
          <RadixSelect.Content className={styles.content} position="popper" sideOffset={4}>
            <RadixSelect.Viewport>
              {options.map((o) => (
                <RadixSelect.Item key={o.value} value={o.value} className={styles.item}>
                  <RadixSelect.ItemText>{o.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <Check size={16} weight="bold" />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}
