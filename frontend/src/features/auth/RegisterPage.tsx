import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Input } from '@/components/Input/Input'
import { Select } from '@/components/Select/Select'
import { ApiError } from '@/lib/api'
import { useCities } from '@/lib/catalog'
import { useAuth } from './AuthContext'
import styles from './Auth.module.css'

type Kind = 'particulier' | 'boutique'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const cities = useCities()
  const [kind, setKind] = useState<Kind>('particulier')
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    shop_name: '',
    email: '',
    phone: '',
    password: '',
    city: '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    setFormError('')
    try {
      await register({
        ...form,
        account_type: kind,
        shop_name: kind === 'boutique' ? form.shop_name : undefined,
      })
      navigate(kind === 'boutique' ? '/compte' : '/vendre', { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fields)
        if (Object.keys(err.fields).length === 0) setFormError(err.message)
      } else {
        setFormError('Inscription impossible. Réessayez.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Créer un compte</h1>
      <p className={styles.lead}>
        Gratuit. Vous publiez votre première annonce en quelques minutes.
      </p>
      <form className={styles.form} onSubmit={submit} noValidate>
        {formError && (
          <p className={styles.formError} role="alert">
            {formError}
          </p>
        )}
        <div className={styles.kinds} role="group" aria-label="Type de compte">
          <button
            type="button"
            className={styles.kind}
            aria-pressed={kind === 'particulier'}
            onClick={() => setKind('particulier')}
          >
            <span className={styles.kindName}>Particulier</span>
            <span className={styles.kindHint}>Je vends mes appareils</span>
          </button>
          <button
            type="button"
            className={styles.kind}
            aria-pressed={kind === 'boutique'}
            onClick={() => setKind('boutique')}
          >
            <span className={styles.kindName}>Boutique</span>
            <span className={styles.kindHint}>Je vends en professionnel</span>
          </button>
        </div>
        {kind === 'boutique' && (
          <Input
            label="Nom de la boutique"
            value={form.shop_name}
            onChange={set('shop_name')}
            error={errors.shop_name}
          />
        )}
        <Input
          label="Prénom"
          autoComplete="given-name"
          value={form.first_name}
          onChange={set('first_name')}
          error={errors.first_name}
        />
        <Input
          label="Nom (facultatif)"
          autoComplete="family-name"
          value={form.last_name}
          onChange={set('last_name')}
          error={errors.last_name}
        />
        <Input
          label="E-mail"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={set('email')}
          error={errors.email}
        />
        <Input
          label="Téléphone"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          hint="Numéro béninois, par exemple 01 97 00 00 00"
          value={form.phone}
          onChange={set('phone')}
          error={errors.phone}
        />
        <Select
          label="Ville"
          placeholder="Choisir une ville"
          options={(cities.data ?? []).map((c) => ({ value: c.name, label: c.name }))}
          value={form.city}
          onValueChange={(city) => setForm((f) => ({ ...f, city }))}
          error={errors.city}
        />
        <Input
          label="Mot de passe"
          type="password"
          autoComplete="new-password"
          hint="8 caractères minimum"
          value={form.password}
          onChange={set('password')}
          error={errors.password}
        />
        <Button type="submit" size="lg" disabled={busy}>
          {busy ? 'Création…' : 'Créer mon compte'}
        </Button>
      </form>
      <p className={styles.switch}>
        Déjà inscrit ? <Link to="/connexion">Se connecter</Link>
      </p>
    </div>
  )
}
