import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { Field } from '@/components/Field/Field'
import fieldStyles from '@/components/Field/Field.module.css'
import { Input } from '@/components/Input/Input'
import { Tag, type TagTone } from '@/components/Tag/Tag'
import { ApiError, api } from '@/lib/api'
import type { User } from '@/lib/types'
import styles from './AccountPage.module.css'

const STATUS: Record<string, { label: string; tone: TagTone }> = {
  none: { label: 'Non vérifié', tone: 'neutral' },
  pending: { label: 'En cours d’examen', tone: 'yellow' },
  verified: { label: 'Vérifié', tone: 'green' },
  rejected: { label: 'Refusé', tone: 'red' },
}

function FileField({ label, name, error }: { label: string; name: string; error?: string }) {
  return (
    <Field label={label} error={error} hint="Photo (JPEG, PNG, WebP) ou PDF, 8 Mo maximum.">
      {({ id, describedBy, invalid }) => (
        <input
          id={id}
          name={name}
          type="file"
          accept="image/*,application/pdf"
          aria-describedby={describedBy}
          aria-invalid={invalid}
          className={fieldStyles.control}
        />
      )}
    </Field>
  )
}

function useUpload(path: string, onDone: () => void) {
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setMessage('')
    try {
      await api(path, { method: 'POST', form: new FormData(e.currentTarget) })
      setMessage('Dossier envoyé. Un modérateur le vérifie, vous serez prévenu ici.')
      onDone()
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields)
        if (Object.keys(err.fields).length === 0) setMessage(err.message)
      } else setMessage('Envoi impossible. Réessayez.')
    } finally {
      setBusy(false)
    }
  }
  return { errors, message, busy, submit }
}

export function VerificationTab({ user }: { user: User }) {
  const queryClient = useQueryClient()
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ['me'] })
  const identity = useUpload('me/identity/', refresh)
  const shop = useUpload('shop/verification/', refresh)
  const idStatus = STATUS[user.identity_status] ?? STATUS.none!
  const shopStatus = user.shop ? (STATUS[user.shop.verification_status] ?? STATUS.none!) : null

  return (
    <div className={styles.verif}>
      {user.account_type === 'boutique' && user.shop ? (
        <section aria-labelledby="shop-verif">
          <h2 id="shop-verif" className={styles.h2}>
            Boutique vérifiée <Tag tone={shopStatus!.tone}>{shopStatus!.label}</Tag>
          </h2>
          <p className={styles.help}>
            Le badge rassure les acheteurs. Un modérateur contrôle votre IFU, votre RCCM et votre
            adresse. Les documents sont supprimés 90 jours après la décision.
          </p>
          {user.shop.verification_status !== 'verified' &&
            user.shop.verification_status !== 'pending' && (
              <form className={styles.form} onSubmit={shop.submit} noValidate>
                {shop.message && <p role="status">{shop.message}</p>}
                <Input label="Numéro IFU" name="ifu" error={shop.errors.ifu} />
                <Input label="Numéro RCCM" name="rccm" error={shop.errors.rccm} />
                <Input
                  label="Adresse de la boutique"
                  name="address"
                  defaultValue={user.shop.address}
                  error={shop.errors.address}
                />
                <FileField
                  label="Justificatif (extrait RCCM ou attestation IFU)"
                  name="document"
                  error={shop.errors.document}
                />
                <Button type="submit" disabled={shop.busy}>
                  {shop.busy ? 'Envoi…' : 'Envoyer mon dossier'}
                </Button>
              </form>
            )}
        </section>
      ) : (
        <section aria-labelledby="id-verif">
          <h2 id="id-verif" className={styles.h2}>
            Identité vérifiée <Tag tone={idStatus.tone}>{idStatus.label}</Tag>
          </h2>
          <p className={styles.help}>
            Envoyez une pièce d’identité (CNI, passeport ou carte biométrique) et un selfie. Un
            modérateur les contrôle. Les documents sont supprimés 90 jours après la décision.
          </p>
          {user.identity_status !== 'verified' && user.identity_status !== 'pending' && (
            <form className={styles.form} onSubmit={identity.submit} noValidate>
              {identity.message && <p role="status">{identity.message}</p>}
              <FileField
                label="Pièce d’identité"
                name="document"
                error={identity.errors.document}
              />
              <FileField
                label="Selfie avec la pièce"
                name="selfie"
                error={identity.errors.selfie}
              />
              <Button type="submit" disabled={identity.busy}>
                {identity.busy ? 'Envoi…' : 'Envoyer mes documents'}
              </Button>
            </form>
          )}
        </section>
      )}
    </div>
  )
}
