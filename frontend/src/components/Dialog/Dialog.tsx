import * as RadixDialog from '@radix-ui/react-dialog'
import { X } from '@phosphor-icons/react'
import type { ReactNode } from 'react'
import styles from './Dialog.module.css'

type Props = {
  trigger: ReactNode
  title: string
  description?: string
  children: ReactNode
}

export function Dialog({ trigger, title, description, children }: Props) {
  return (
    <RadixDialog.Root>
      <RadixDialog.Trigger asChild>{trigger}</RadixDialog.Trigger>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className={styles.overlay} />
        <RadixDialog.Content className={styles.content}>
          <div className={styles.head}>
            <RadixDialog.Title className={styles.title}>{title}</RadixDialog.Title>
            <RadixDialog.Close className={styles.close} aria-label="Fermer">
              <X size={20} />
            </RadixDialog.Close>
          </div>
          {description ? (
            <RadixDialog.Description className={styles.desc}>{description}</RadixDialog.Description>
          ) : (
            <RadixDialog.Description className={styles.sr}>{title}</RadixDialog.Description>
          )}
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  )
}
