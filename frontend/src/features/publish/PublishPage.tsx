import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { Stepper } from '@/components/Stepper/Stepper'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import type { ListingDetailApi, Photo } from '@/lib/types'
import { EMPTY_DRAFT, fromListing, toPayload, type Draft } from './draft'
import {
  StepCondition,
  StepDevice,
  StepHandover,
  StepPhotos,
  StepPrice,
  StepReview,
  StepSpecs,
} from './Steps'
import { filledLabels, voiceToDraft } from './voice'
import styles from './PublishPage.module.css'

const STEPS = ['Appareil', 'État', 'Détails', 'Photos', 'Prix', 'Remise en main', 'Publier']

const FIELD_STEP: Record<string, number> = {
  category: 1,
  device_model: 1,
  brand: 1,
  grade: 2,
  battery_health_pct: 2,
  ram_gb: 3,
  storage_gb: 3,
  photos: 4,
  price_fcfa: 5,
  description: 5,
  city: 6,
  imei_or_serial: 6,
  account_removed: 6,
}

/** Handles access and, when resuming a draft, loads it before the wizard mounts. */
export default function PublishPage() {
  const { id } = useParams()
  const { user, loading } = useAuth()
  const location = useLocation()
  const existing = useQuery({
    queryKey: ['my-listing', id],
    queryFn: () => api<ListingDetailApi>(`listings/${id}/`),
    enabled: Boolean(id) && Boolean(user),
    gcTime: 0,
  })

  if (loading) return <p>Chargement…</p>
  if (!user) {
    return <Navigate to="/connexion" replace state={{ from: location.pathname }} />
  }
  if (id && existing.isPending) return <p>Chargement du brouillon…</p>
  if (id && existing.isError) return <p>Ce brouillon est introuvable.</p>

  const initial = existing.data
    ? fromListing(existing.data)
    : { ...EMPTY_DRAFT, city: user.city, quartier: user.quartier }
  return (
    <Wizard
      key={id ?? 'new'}
      initialDraft={initial}
      initialPhotos={existing.data?.photos ?? []}
      initialId={existing.data?.id ?? null}
    />
  )
}

function Wizard({
  initialDraft,
  initialPhotos,
  initialId,
}: {
  initialDraft: Draft
  initialPhotos: Photo[]
  initialId: number | null
}) {
  const navigate = useNavigate()
  const { notify } = useToast()

  const [step, setStep] = useState(1)
  const [draft, setDraft] = useState<Draft>(initialDraft)
  const [listingId, setListingId] = useState<number | null>(initialId)
  const [photos, setPhotos] = useState<Photo[]>(initialPhotos)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [voiceSummary, setVoiceSummary] = useState<string[]>([])
  const [suggesting, setSuggesting] = useState(false)
  const [suggestedByAi, setSuggestedByAi] = useState(false)

  const patch = (p: Partial<Draft>) => {
    setDraft((d) => ({ ...d, ...p }))
    setErrors((e) => {
      const next = { ...e }
      for (const key of Object.keys(p)) delete next[key]
      return next
    })
  }

  /** Saves the draft on the server so nothing is lost between two steps. */
  async function save(): Promise<number | null> {
    try {
      if (listingId) {
        await api(`listings/${listingId}/`, { method: 'PATCH', body: toPayload(draft) })
        return listingId
      }
      const created = await api<ListingDetailApi>('listings/', {
        method: 'POST',
        body: toPayload(draft),
      })
      setListingId(created.id)
      return created.id
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fields)
        if (Object.keys(e.fields).length === 0) notify(e.message)
      } else notify('Enregistrement impossible. Réessayez.')
      return null
    }
  }

  function localErrors(): Record<string, string> {
    const out: Record<string, string> = {}
    if (step === 1) {
      if (!draft.category) out.category = 'Choisissez ce que vous vendez.'
      else if (!draft.device_model && !(draft.custom_model_name && draft.custom_brand))
        out.device_model = 'Choisissez un modèle dans la liste ou saisissez le vôtre.'
    }
    if (
      step === 2 &&
      draft.condition_type !== 'new_sealed' &&
      draft.condition_type !== 'new_open' &&
      !draft.grade
    )
      out.grade = 'Choisissez la note d’état.'
    if (step === 5 && !Number(draft.price_fcfa)) out.price_fcfa = 'Indiquez un prix en FCFA.'
    if (step === 6 && !draft.city) out.city = 'Indiquez la ville où se trouve l’appareil.'
    return out
  }

  async function next() {
    const local = localErrors()
    if (Object.keys(local).length > 0) {
      setErrors(local)
      return
    }
    setBusy(true)
    const saved = await save()
    setBusy(false)
    if (saved) {
      setErrors({})
      setStep((s) => Math.min(STEPS.length, s + 1))
      window.scrollTo({ top: 0 })
    }
  }

  async function publish() {
    setBusy(true)
    const saved = await save()
    if (!saved) {
      setBusy(false)
      return
    }
    try {
      const result = await api<ListingDetailApi>(`listings/${saved}/publish/`, { method: 'POST' })
      if (result.status === 'pending_review') {
        notify('Annonce envoyée. Elle sera en ligne après relecture.')
        navigate('/compte', { replace: true })
      } else {
        notify('Votre annonce est en ligne.')
        navigate(`/annonce/${result.slug}`, { replace: true })
      }
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fields)
        const first = Object.keys(e.fields)
          .map((k) => FIELD_STEP[k])
          .filter((n): n is number => n !== undefined)
          .sort()[0]
        if (first && first !== STEPS.length) setStep(first)
        if (Object.keys(e.fields).length === 0) notify(e.message)
      } else notify('Publication impossible. Réessayez.')
    } finally {
      setBusy(false)
    }
  }

  /** Dictation: pre-fills the form; the seller validates it step by step. */
  function applyVoice(result: Parameters<typeof voiceToDraft>[0]) {
    const filled = voiceToDraft(result, draft)
    patch(filled)
    setVoiceSummary(filledLabels(filled))
    if (Object.keys(filled).length === 0)
      notify('Rien de précis n’a été reconnu. Réessayez ou saisissez à la main.')
  }

  /** « Rédaction assistée »: saves the draft first so the text is written from what is entered. */
  async function suggestDescription() {
    setSuggesting(true)
    try {
      const saved = await save()
      if (!saved) return
      const text = await api<{ description: string; used_ai: boolean }>('ai/describe/', {
        method: 'POST',
        body: { listing_id: saved },
      })
      patch({ description: text.description })
      setSuggestedByAi(text.used_ai)
    } catch (e) {
      notify(e instanceof ApiError ? e.message : 'La rédaction n’a pas abouti.')
    } finally {
      setSuggesting(false)
    }
  }

  const props = { draft, patch, errors }
  const last = step === STEPS.length

  return (
    <div className={styles.page}>
      <h1 className={styles.title}>Vendre un appareil</h1>
      <Stepper steps={STEPS} current={step} />
      <form
        className={styles.card}
        onSubmit={(e) => {
          e.preventDefault()
          void (last ? publish() : next())
        }}
      >
        <h2 className={styles.stepTitle}>{STEPS[step - 1]}</h2>
        {step === 1 && <StepDevice {...props} onVoice={applyVoice} voiceSummary={voiceSummary} />}
        {step === 2 && <StepCondition {...props} />}
        {step === 3 && <StepSpecs {...props} />}
        {step === 4 && listingId && (
          <StepPhotos {...props} photos={photos} listingId={listingId} onPhotosChange={setPhotos} />
        )}
        {step === 5 && (
          <StepPrice
            {...props}
            onSuggest={() => void suggestDescription()}
            suggesting={suggesting}
            suggestedByAi={suggestedByAi}
          />
        )}
        {step === 6 && <StepHandover {...props} />}
        {step === 7 && <StepReview {...props} photos={photos} />}

        <div className={styles.actions}>
          {step > 1 && (
            <Button variant="secondary" size="lg" onClick={() => setStep(step - 1)} disabled={busy}>
              Retour
            </Button>
          )}
          <Button type="submit" size="lg" disabled={busy}>
            {busy ? 'Enregistrement…' : last ? 'Publier mon annonce' : 'Continuer'}
          </Button>
        </div>
        <p className={styles.saved}>Votre brouillon est enregistré à chaque étape.</p>
      </form>
    </div>
  )
}
