import * as RadixTabs from '@radix-ui/react-tabs'
import type { ReactNode } from 'react'
import styles from './Tabs.module.css'

export type TabItem = { value: string; label: string; content: ReactNode }

export function Tabs({ items, defaultValue }: { items: TabItem[]; defaultValue?: string }) {
  return (
    <RadixTabs.Root defaultValue={defaultValue ?? items[0]?.value}>
      <RadixTabs.List className={styles.list}>
        {items.map((t) => (
          <RadixTabs.Trigger key={t.value} value={t.value} className={styles.trigger}>
            {t.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {items.map((t) => (
        <RadixTabs.Content key={t.value} value={t.value} className={styles.content}>
          {t.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  )
}
