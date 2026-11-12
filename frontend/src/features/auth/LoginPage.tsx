import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Input } from '@/components/Input/Input'
import { ApiError } from '@/lib/api'
import { useAuth } from './AuthContext'
import styles from './Auth.module.css'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/compte'
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(identifier.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Connexion impossible. Réessayez.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Connexion</h1>
      <p className={styles.lead}>
        Connectez-vous pour vendre, contacter un vendeur ou gérer vos favoris.
      </p>
      <form className={styles.form} onSubmit={submit} noValidate>
        {error && (
          <p className={styles.formError} role="alert">
            {error}
          </p>
        )}
        <Input
          label="E-mail ou téléphone"
          autoComplete="username"
          inputMode="email"
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
        <Input
          label="Mot de passe"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Button type="submit" size="lg" disabled={busy || !identifier || !password}>
          {busy ? 'Connexion…' : 'Se connecter'}
        </Button>
      </form>
      <p className={styles.switch}>
        Pas encore de compte ? <Link to="/inscription">Créer un compte</Link>
      </p>
    </div>
  )
}
