import { Flag } from '@phosphor-icons/react'
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Dialog } from '@/components/Dialog/Dialog'
import { Radio } from '@/components/Choice/Choice'
import { Textarea } from '@/components/Input/Input'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import styles from './ReportDialog.module.css'

const REASONS = [
  ['scam', 'Arnaque ou demande de paiement suspecte'],
  ['stolen', 'Appareil probablement volé'],
  ['wrong_info', 'Informations fausses'],
  ['duplicate', 'Annonce en double'],
  ['other', 'Autre'],
] as const

export function ReportDialog({ listingId }: { listingId: number }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [reason, setReason] = useState('')
  const [details, setDetails] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!reason) {
      setError('Choisissez un motif.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await api(`listings/${listingId}/report/`, { method: 'POST', body: { reason, details } })
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Signalement impossible.')
    } finally {
      setBusy(false)
    }
  }

  const trigger = (
    <Button
      variant="ghost"
      onClick={(e) => {
        if (!user) {
          e.preventDefault()
          navigate('/connexion', { state: { from: location.pathname } })
        }
      }}
    >
      <Flag size={18} aria-hidden /> Signaler cette annonce
    </Button>
  )

  if (!user) return trigger

  return (
    <Dialog
      trigger={trigger}
      title="Signaler cette annonce"
      description="Notre équipe examine chaque signalement."
    >
      {done ? (
        <p role="status">Merci, votre signalement a bien été envoyé.</p>
      ) : (
        <form className={styles.form} onSubmit={submit}>
          <fieldset className={styles.group}>
            <legend>Motif</legend>
            {REASONS.map(([value, label]) => (
              <Radio
                key={value}
                name="reason"
                label={label}
                checked={reason === value}
                onChange={() => setReason(value)}
              />
            ))}
          </fieldset>
          <Textarea
            label="Précisions (facultatif)"
            rows={3}
            maxLength={1000}
            value={details}
            onChange={(e) => setDetails(e.target.value)}
          />
          {error && (
            <p className={styles.error} role="alert">
              {error}
            </p>
          )}
          <Button type="submit" disabled={busy}>
            {busy ? 'Envoi…' : 'Envoyer le signalement'}
          </Button>
        </form>
      )}
    </Dialog>
  )
}
