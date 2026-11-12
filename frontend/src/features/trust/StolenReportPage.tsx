import { useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { Input, Textarea } from '@/components/Input/Input'
import { ApiError, api } from '@/lib/api'
import styles from '@/features/auth/Auth.module.css'

export default function StolenReportPage() {
  const [form, setForm] = useState({ imei_or_serial: '', description: '', police_reference: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError('')
    try {
      await api('stolen-reports/', { method: 'POST', body: form })
      setDone(true)
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields)
        if (Object.keys(err.fields).length === 0) setFormError(err.message)
      } else setFormError('Envoi impossible. Réessayez.')
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className={styles.page}>
        <h1 className={styles.title}>Déclaration reçue</h1>
        <p className={styles.lead} role="status">
          Merci. Notre équipe vérifie votre déclaration. Une fois confirmée, aucune annonce portant
          ce numéro ne pourra être publiée.
        </p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Déclarer un appareil volé</h1>
      <p className={styles.lead}>
        Indiquez l’IMEI (composez *#06# ou voyez la boîte) ou le numéro de série. Il n’est jamais
        publié : nous n’en gardons qu’une empreinte pour bloquer les annonces.
      </p>
      <form className={styles.form} onSubmit={submit} noValidate>
        {formError && (
          <p className={styles.formError} role="alert">
            {formError}
          </p>
        )}
        <Input
          label="IMEI ou numéro de série"
          value={form.imei_or_serial}
          onChange={set('imei_or_serial')}
          error={errors.imei_or_serial}
        />
        <Textarea
          label="Que s’est-il passé ?"
          rows={4}
          maxLength={2000}
          value={form.description}
          onChange={set('description')}
          error={errors.description}
        />
        <Input
          label="Référence de la plainte (facultatif)"
          value={form.police_reference}
          onChange={set('police_reference')}
          error={errors.police_reference}
        />
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? 'Envoi…' : 'Envoyer la déclaration'}
        </Button>
      </form>
    </div>
  )
}
