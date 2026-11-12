import * as RadixPopover from '@radix-ui/react-popover'
import type { ReactNode } from 'react'
import styles from './Popover.module.css'

export function Popover({ trigger, children }: { trigger: ReactNode; children: ReactNode }) {
  return (
    <RadixPopover.Root>
      <RadixPopover.Trigger asChild>{trigger}</RadixPopover.Trigger>
      <RadixPopover.Portal>
        <RadixPopover.Content className={styles.content} sideOffset={6} align="start">
          {children}
        </RadixPopover.Content>
      </RadixPopover.Portal>
    </RadixPopover.Root>
  )
}
