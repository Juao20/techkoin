import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { Input, Textarea } from '@/components/Input/Input'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import type { Shop, User } from '@/lib/types'
import styles from './Pro.module.css'

type Form = Pick<Shop, 'name' | 'description' | 'address' | 'city' | 'quartier' | 'whatsapp_number'>

export default function SettingsTab() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const shop = user?.shop
  const [form, setForm] = useState<Form>({
    name: shop?.name ?? '',
    description: shop?.description ?? '',
    address: shop?.address ?? '',
    city: shop?.city ?? '',
    quartier: shop?.quartier ?? '',
    whatsapp_number: shop?.whatsapp_number ?? '',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const set = (k: keyof Form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setErrors({})
    try {
      const updated = await api<Shop>('shop/', { method: 'PATCH', body: form })
      queryClient.setQueryData<{ user: User | null }>(['me'], (me) =>
        me?.user ? { user: { ...me.user, shop: updated } } : (me ?? { user: null }),
      )
      notify('Boutique enregistrée.')
    } catch (err) {
      if (err instanceof ApiError) setErrors(err.fields)
      notify(err instanceof ApiError ? err.message : 'Enregistrement impossible.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className={styles.form} onSubmit={submit} noValidate>
      <p className={styles.hint}>
        Ces informations apparaissent sur votre vitrine publique.
        {shop?.is_verified ? ' Votre boutique est vérifiée.' : ''}
      </p>
      <Input
        label="Nom de la boutique"
        value={form.name}
        onChange={set('name')}
        error={errors.name}
      />
      <Textarea
        label="Présentation"
        rows={4}
        value={form.description}
        onChange={set('description')}
        error={errors.description}
      />
      <Input
        label="Adresse"
        value={form.address}
        onChange={set('address')}
        error={errors.address}
      />
      <Input label="Ville" value={form.city} onChange={set('city')} error={errors.city} />
      <Input
        label="Quartier"
        value={form.quartier}
        onChange={set('quartier')}
        error={errors.quartier}
      />
      <Input
        label="Numéro WhatsApp de la boutique"
        type="tel"
        hint="Utilisé quand un acheteur vous écrit depuis une annonce."
        value={form.whatsapp_number}
        onChange={set('whatsapp_number')}
        error={errors.whatsapp_number}
      />
      <Button type="submit" size="lg" disabled={busy}>
        {busy ? 'Enregistrement…' : 'Enregistrer'}
      </Button>
    </form>
  )
}
