import { useQuery } from '@tanstack/react-query'
import { useRef, useState, type ReactNode } from 'react'
import { Button } from '@/components/Button/Button'
import { Checkbox, Radio } from '@/components/Choice/Choice'
import { Field } from '@/components/Field/Field'
import fieldStyles from '@/components/Field/Field.module.css'
import { Input, Textarea } from '@/components/Input/Input'
import { PriceRange } from '@/components/PriceRange/PriceRange'
import { Tag } from '@/components/Tag/Tag'
import { api } from '@/lib/api'
import { useBrands, useCities } from '@/lib/catalog'
import { formatFCFA } from '@/lib/format'
import { CATEGORY_LABELS, CONDITION_LABELS } from '@/lib/listings'
import type { Category, Photo } from '@/lib/types'
import { BADGES } from '@/lib/usage'
import { useDebounced } from '@/lib/useDebounced'
import { Autocomplete } from './Autocomplete'
import { isComputer, isMobile, isNew, type Draft } from './draft'
import { proposeGrade, type GradeAnswers, type Wear } from './grade'
import { resizeImage } from './image'
import styles from './Steps.module.css'

export type StepProps = {
  draft: Draft
  patch: (p: Partial<Draft>) => void
  errors: Record<string, string>
}

type ModelHit = { slug: string; label: string; name: string; brand: string; category: Category }
type ModelDetail = {
  ram_options_gb: number[]
  storage_options_gb: number[]
  has_5g: boolean
  dual_sim: boolean
  esim: boolean
  cellular_option: boolean
  stylus_support: boolean
  default_processor: { id: number; name: string } | null
  default_gpu: { id: number; name: string } | null
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className={styles.group}>
      <legend className={styles.legend}>{title}</legend>
      {children}
    </fieldset>
  )
}

/* ---------- 1. Appareil ---------- */

export function StepDevice({ draft, patch, errors }: StepProps) {
  const brands = useBrands(draft.category || undefined)
  const [custom, setCustom] = useState(Boolean(draft.custom_model_name))

  async function pick(hit: ModelHit) {
    patch({
      device_model: hit.slug,
      device_label: hit.label,
      category: hit.category,
      custom_model_name: '',
    })
    try {
      const m = await api<ModelDetail>(`catalog/models/${hit.slug}/`)
      patch({
        ram_gb: m.ram_options_gb.length === 1 ? String(m.ram_options_gb[0]) : '',
        storage_gb: m.storage_options_gb.length === 1 ? String(m.storage_options_gb[0]) : '',
        network_5g: m.has_5g,
        dual_sim: m.dual_sim,
        processor: m.default_processor?.id ?? null,
        processor_label: m.default_processor?.name ?? '',
        gpu: m.default_gpu?.id ?? null,
        gpu_label: m.default_gpu?.name ?? '',
      })
    } catch {
      /* The seller can still fill the specs by hand. */
    }
  }

  return (
    <>
      <Group title="Que vendez-vous ?">
        <div className={styles.tiles}>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={styles.tile}
              aria-pressed={draft.category === value}
              onClick={() =>
                patch({ category: value as Category, device_model: '', device_label: '' })
              }
            >
              {label}
            </button>
          ))}
        </div>
        {errors.category && <p className={styles.error}>{errors.category}</p>}
      </Group>

      {draft.category && !custom && (
        <>
          <Autocomplete<ModelHit>
            label="Modèle"
            hint="Tapez le nom, par exemple iPhone 13 ou ThinkPad T14."
            error={errors.device_model}
            path="catalog/models/"
            extraQuery={{ category: draft.category }}
            getLabel={(m) => m.label}
            initial={draft.device_label}
            onPick={(m) => void pick(m)}
          />
          <Button variant="ghost" onClick={() => setCustom(true)}>
            Mon modèle n’est pas dans la liste
          </Button>
        </>
      )}

      {draft.category && custom && (
        <>
          <Field label="Marque" error={errors.brand}>
            {({ id }) => (
              <select
                id={id}
                className={fieldStyles.control}
                value={draft.custom_brand}
                onChange={(e) => patch({ custom_brand: e.target.value })}
              >
                <option value="">Choisir une marque</option>
                {(brands.data ?? []).map((b) => (
                  <option key={b.slug} value={b.slug}>
                    {b.name}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <Input
            label="Nom du modèle"
            hint="Votre annonce sera relue par l’équipe avant d’être publiée."
            value={draft.custom_model_name}
            onChange={(e) => patch({ custom_model_name: e.target.value, device_model: '' })}
            error={errors.device_model}
          />
          <Button
            variant="ghost"
            onClick={() => {
              setCustom(false)
              patch({ custom_model_name: '', custom_brand: '' })
            }}
          >
            Chercher dans la liste
          </Button>
        </>
      )}
    </>
  )
}

/* ---------- 2. État ---------- */

const WEAR: Array<{ value: Wear; label: string }> = [
  { value: 'none', label: 'Aucune' },
  { value: 'light', label: 'Légères' },
  { value: 'visible', label: 'Visibles' },
]

export function StepCondition({ draft, patch, errors }: StepProps) {
  const a = draft.answers
  const setAnswer = (p: Partial<GradeAnswers>) => {
    const answers = { ...a, ...p }
    patch({ answers, grade: proposeGrade(answers).grade })
  }
  const proposal = proposeGrade(a)

  return (
    <>
      <Group title="État de l’appareil">
        {(Object.keys(CONDITION_LABELS) as Array<Draft['condition_type']>).map((value) => (
          <Radio
            key={value}
            name="condition"
            label={CONDITION_LABELS[value] ?? value}
            checked={draft.condition_type === value}
            onChange={() =>
              patch({
                condition_type: value,
                grade: value.startsWith('new') ? '' : proposeGrade(a).grade,
              })
            }
          />
        ))}
      </Group>

      {!isNew(draft) && (
        <>
          <Group title="Rayures sur l’écran">
            {WEAR.map((w) => (
              <Radio
                key={w.value}
                name="screen-wear"
                label={w.label}
                checked={a.screen === w.value}
                onChange={() => setAnswer({ screen: w.value })}
              />
            ))}
          </Group>
          <Group title="Traces sur le châssis">
            {WEAR.map((w) => (
              <Radio
                key={w.value}
                name="body-wear"
                label={w.label}
                checked={a.body === w.value}
                onChange={() => setAnswer({ body: w.value })}
              />
            ))}
          </Group>
          <Group title="Autres points">
            <Checkbox
              label="L’écran est fissuré"
              checked={a.screenCracked}
              onChange={(e) => setAnswer({ screenCracked: e.target.checked })}
            />
            <Checkbox
              label="La batterie tient moins bien qu’au début"
              checked={a.batteryWeak}
              onChange={(e) => setAnswer({ batteryWeak: e.target.checked })}
            />
            <Checkbox
              label="Tout fonctionne : boutons, ports, caméras, réseau"
              checked={a.fullyWorking}
              onChange={(e) => setAnswer({ fullyWorking: e.target.checked })}
            />
          </Group>

          <div className={styles.proposal} role="status">
            <p className={styles.proposalTitle}>
              Note proposée :{' '}
              <Tag tone={draft.grade === 'A' ? 'green' : 'neutral'}>
                {draft.grade || proposal.grade}
              </Tag>
            </p>
            <p className={styles.hint}>{proposal.reasons.join(', ')}.</p>
            <div className={styles.row}>
              {(['A', 'B', 'C'] as const).map((g) => (
                <Radio
                  key={g}
                  name="grade"
                  label={`${g} · ${{ A: 'Comme neuf', B: 'Bon état', C: 'Traces visibles' }[g]}`}
                  checked={draft.grade === g}
                  onChange={() => patch({ grade: g })}
                />
              ))}
            </div>
            {errors.grade && <p className={styles.error}>{errors.grade}</p>}
          </div>
        </>
      )}

      {isMobile(draft) && (
        <Input
          label="Santé de la batterie (%)"
          hint="Sur iPhone : Réglages, Batterie, Santé de la batterie."
          inputMode="numeric"
          value={draft.battery_health_pct}
          onChange={(e) => patch({ battery_health_pct: e.target.value.replace(/\D/g, '') })}
          error={errors.battery_health_pct}
        />
      )}
    </>
  )
}

/* ---------- 3. Caractéristiques ---------- */

export function StepSpecs({ draft, patch, errors }: StepProps) {
  return (
    <>
      <div className={styles.row}>
        <Input
          label="Mémoire vive (Go)"
          inputMode="numeric"
          value={draft.ram_gb}
          onChange={(e) => patch({ ram_gb: e.target.value.replace(/\D/g, '') })}
          error={errors.ram_gb}
        />
        <Input
          label="Stockage (Go)"
          inputMode="numeric"
          value={draft.storage_gb}
          onChange={(e) => patch({ storage_gb: e.target.value.replace(/\D/g, '') })}
          error={errors.storage_gb}
        />
      </div>
      <Input
        label="Couleur"
        value={draft.color}
        onChange={(e) => patch({ color: e.target.value })}
      />

      {isComputer(draft) && (
        <>
          <Field label="Type de stockage">
            {({ id }) => (
              <select
                id={id}
                className={fieldStyles.control}
                value={draft.storage_type}
                onChange={(e) => patch({ storage_type: e.target.value })}
              >
                <option value="">Choisir</option>
                <option value="ssd">SSD</option>
                <option value="hdd">HDD</option>
                <option value="hybrid">Hybride</option>
              </select>
            )}
          </Field>
          <Autocomplete<{ id: number; name: string }>
            label="Processeur"
            hint="Tapez par exemple i5-1135G7 ou Ryzen 5."
            path="catalog/processors/"
            getLabel={(p) => p.name}
            initial={draft.processor_label}
            onPick={(p) => patch({ processor: p.id, processor_label: p.name })}
          />
          <Autocomplete<{ id: number; name: string }>
            label="Carte graphique dédiée (facultatif)"
            path="catalog/gpus/"
            getLabel={(g) => g.name}
            initial={draft.gpu_label}
            onPick={(g) => patch({ gpu: g.id, gpu_label: g.name })}
          />
          <Field label="Clavier">
            {({ id }) => (
              <select
                id={id}
                className={fieldStyles.control}
                value={draft.keyboard_layout}
                onChange={(e) => patch({ keyboard_layout: e.target.value })}
              >
                <option value="">Choisir</option>
                <option value="azerty">AZERTY</option>
                <option value="qwerty">QWERTY</option>
                <option value="qwertz">QWERTZ</option>
              </select>
            )}
          </Field>
        </>
      )}

      {isMobile(draft) && (
        <Group title="Téléphone">
          <Checkbox
            label="5G"
            checked={draft.network_5g}
            onChange={(e) => patch({ network_5g: e.target.checked })}
          />
          <Checkbox
            label="Double SIM"
            checked={draft.dual_sim}
            onChange={(e) => patch({ dual_sim: e.target.checked })}
          />
          <Checkbox
            label="Débloqué tout opérateur"
            checked={draft.carrier_unlocked}
            onChange={(e) => patch({ carrier_unlocked: e.target.checked })}
          />
          <Checkbox
            label="Écran d’origine, jamais remplacé"
            checked={draft.screen_original}
            onChange={(e) => patch({ screen_original: e.target.checked })}
          />
          <Checkbox
            label="Face ID, empreinte et capteurs fonctionnent"
            checked={draft.biometrics_ok}
            onChange={(e) => patch({ biometrics_ok: e.target.checked })}
          />
          {draft.category === 'tablet' && (
            <>
              <Checkbox
                label="Avec carte SIM"
                checked={draft.cellular}
                onChange={(e) => patch({ cellular: e.target.checked })}
              />
              <Checkbox
                label="Stylet inclus"
                checked={draft.stylus_included}
                onChange={(e) => patch({ stylus_included: e.target.checked })}
              />
            </>
          )}
        </Group>
      )}
    </>
  )
}

/* ---------- 4. Photos ---------- */

type PhotoStepProps = StepProps & {
  photos: Photo[]
  listingId: number
  onPhotosChange: (photos: Photo[]) => void
}

const SLOTS = [
  { kind: 'front', label: 'Face avant', required: true },
  { kind: 'back', label: 'Face arrière', required: true },
  { kind: 'screen_on', label: 'Écran allumé', required: true },
  { kind: 'defect', label: 'Photo du défaut', required: false },
  { kind: 'other', label: 'Autre photo', required: false },
] as const

export function StepPhotos({ draft, photos, listingId, onPhotosChange, errors }: PhotoStepProps) {
  const [busy, setBusy] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const inputs = useRef<Record<string, HTMLInputElement | null>>({})
  const needsDefect = draft.grade === 'C' && !isNew(draft)

  async function upload(kind: string, file: File) {
    setBusy(kind)
    setMessage('')
    try {
      const small = await resizeImage(file)
      const form = new FormData()
      form.append('image', small, 'photo.jpg')
      form.append('kind', kind)
      const photo = await api<Photo>(`listings/${listingId}/photos/`, { method: 'POST', form })
      onPhotosChange([...photos, photo])
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'La photo n’a pas pu être envoyée.')
    } finally {
      setBusy(null)
    }
  }

  async function remove(photo: Photo) {
    try {
      await api(`listings/${listingId}/photos/${photo.id}/`, { method: 'DELETE' })
      onPhotosChange(photos.filter((p) => p.id !== photo.id))
    } catch (e) {
      setMessage(e instanceof Error ? e.message : 'Suppression impossible.')
    }
  }

  return (
    <>
      <p className={styles.hint}>
        Entre 4 et 10 photos. Prenez-les à la lumière du jour, appareil bien visible.
      </p>
      <ul className={styles.slots}>
        {SLOTS.filter((s) => s.kind !== 'defect' || needsDefect).map((slot) => {
          const mine = photos.filter((p) => p.kind === slot.kind)
          return (
            <li key={slot.kind} className={styles.slot}>
              <p className={styles.slotTitle}>
                {slot.label}
                {(slot.required || (slot.kind === 'defect' && needsDefect)) && (
                  <span className={styles.required}> · obligatoire</span>
                )}
              </p>
              <div className={styles.thumbs}>
                {mine.map((p) => (
                  <div key={p.id} className={styles.thumb}>
                    <img src={p.thumb} alt={slot.label} />
                    <button
                      type="button"
                      aria-label={`Supprimer la photo ${slot.label}`}
                      onClick={() => void remove(p)}
                    >
                      ×
                    </button>
                  </div>
                ))}
                {(slot.kind === 'other' || mine.length === 0) && photos.length < 10 && (
                  <>
                    <input
                      ref={(el) => {
                        inputs.current[slot.kind] = el
                      }}
                      type="file"
                      accept="image/*"
                      capture={slot.kind === 'other' ? undefined : 'environment'}
                      hidden
                      onChange={(e) => {
                        const file = e.target.files?.[0]
                        e.target.value = ''
                        if (file) void upload(slot.kind, file)
                      }}
                    />
                    <button
                      type="button"
                      className={styles.add}
                      disabled={busy !== null}
                      onClick={() => inputs.current[slot.kind]?.click()}
                    >
                      {busy === slot.kind ? 'Envoi…' : '+ Ajouter'}
                    </button>
                  </>
                )}
              </div>
            </li>
          )
        })}
      </ul>
      {(message || errors.photos) && (
        <p className={styles.error} role="alert">
          {message || errors.photos}
        </p>
      )}
    </>
  )
}

/* ---------- 5. Prix ---------- */

type EstimateApi =
  | { available: false }
  | {
      available: true
      low: number
      mid: number
      high: number
      sample_size: number
      indicative: boolean
      badge: 'good_deal' | 'fair' | 'above_market' | 'unknown'
    }

function LiveEstimate({ draft, price }: { draft: Draft; price: number }) {
  const debouncedPrice = useDebounced(price, 400)
  const enabled = Boolean(draft.device_model)
  const body = {
    device_model: draft.device_model,
    storage_gb: Number(draft.storage_gb) || null,
    ram_gb: Number(draft.ram_gb) || null,
    condition_type: draft.condition_type,
    grade: isNew(draft) ? '' : draft.grade,
    battery_health_pct: Number(draft.battery_health_pct) || null,
    price_fcfa: debouncedPrice || 0,
  }
  const { data } = useQuery({
    queryKey: ['estimate', body],
    queryFn: () => api<EstimateApi>('pricing/estimate/', { method: 'POST', body }),
    enabled,
    staleTime: 60_000,
  })

  if (!enabled) {
    return (
      <p className={styles.hint}>
        L’estimation est disponible pour les modèles de la liste. Votre annonce sera relue avant
        publication.
      </p>
    )
  }
  if (!data || !data.available) return null
  const badge = data.badge !== 'unknown' ? BADGES[data.badge] : null
  return (
    <div className={styles.estimate} role="status">
      <PriceRange low={data.low} high={data.high} price={price || data.mid} />
      <p className={styles.hint}>
        {data.indicative
          ? 'Estimation indicative : peu d’annonces comparables.'
          : `Calculée sur ${data.sample_size} annonces et ventes comparables.`}
      </p>
      {badge && price > 0 && (
        <p className={styles.badgeLine}>
          Votre annonce sera marquée : <Tag tone={badge.tone}>{badge.label}</Tag>
        </p>
      )}
    </div>
  )
}

export function StepPrice({ draft, patch, errors }: StepProps) {
  const price = Number(draft.price_fcfa.replace(/\s/g, ''))
  return (
    <>
      <Input
        label="Prix (FCFA)"
        inputMode="numeric"
        value={draft.price_fcfa}
        onChange={(e) => patch({ price_fcfa: e.target.value.replace(/\D/g, '') })}
        error={errors.price_fcfa}
        hint={
          price > 0 ? formatFCFA(price) : 'Indiquez le prix que vous voulez réellement recevoir.'
        }
      />
      <LiveEstimate draft={draft} price={price} />
      <Checkbox
        label="Prix négociable"
        checked={draft.negotiable}
        onChange={(e) => patch({ negotiable: e.target.checked })}
      />
      <Textarea
        label="Description (facultatif)"
        hint="Historique, raison de la vente, ce qui est inclus."
        rows={5}
        maxLength={2000}
        value={draft.description}
        onChange={(e) => patch({ description: e.target.value })}
      />
    </>
  )
}

/* ---------- 6. Remise en main ---------- */

const ACCESSORIES = [
  ['charger', 'Chargeur'],
  ['box', 'Boîte'],
  ['cable', 'Câble'],
  ['case', 'Coque'],
  ['earphones', 'Écouteurs'],
  ['invoice', 'Facture'],
] as const

export function StepHandover({ draft, patch, errors }: StepProps) {
  const cities = useCities()
  return (
    <>
      <Field label="Ville" error={errors.city}>
        {({ id }) => (
          <select
            id={id}
            className={fieldStyles.control}
            value={draft.city}
            onChange={(e) => patch({ city: e.target.value })}
          >
            <option value="">Choisir une ville</option>
            {(cities.data ?? []).map((c) => (
              <option key={c.slug} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Input
        label="Quartier (facultatif)"
        value={draft.quartier}
        onChange={(e) => patch({ quartier: e.target.value })}
      />

      <Group title="Fourni avec l’appareil">
        {ACCESSORIES.map(([value, label]) => (
          <Checkbox
            key={value}
            label={label}
            checked={draft.accessories.includes(value)}
            onChange={(e) =>
              patch({
                accessories: e.target.checked
                  ? [...draft.accessories, value]
                  : draft.accessories.filter((x) => x !== value),
              })
            }
          />
        ))}
      </Group>

      <Field label="Garantie">
        {({ id }) => (
          <select
            id={id}
            className={fieldStyles.control}
            value={draft.warranty_months}
            onChange={(e) => patch({ warranty_months: e.target.value })}
          >
            <option value="0">Aucune</option>
            {[1, 3, 6, 12].map((m) => (
              <option key={m} value={m}>
                {m} mois
              </option>
            ))}
          </select>
        )}
      </Field>

      <Input
        label={isMobile(draft) ? 'IMEI (composez *#06#)' : 'Numéro de série'}
        hint="Il est chiffré et n’est jamais affiché aux acheteurs."
        value={draft.imei_or_serial}
        onChange={(e) => patch({ imei_or_serial: e.target.value })}
        error={errors.imei_or_serial}
      />

      {isMobile(draft) && (
        <div>
          <Checkbox
            label="J’ai retiré mon compte iCloud ou Google de l’appareil"
            checked={draft.account_removed}
            onChange={(e) => patch({ account_removed: e.target.checked })}
          />
          {errors.account_removed && <p className={styles.error}>{errors.account_removed}</p>}
        </div>
      )}
    </>
  )
}

/* ---------- 7. Récapitulatif ---------- */

export function StepReview({ draft, photos, errors }: StepProps & { photos: Photo[] }) {
  const missing = Object.entries(errors)
  return (
    <>
      <dl className={styles.recap}>
        <dt>Appareil</dt>
        <dd>{draft.device_label || draft.custom_model_name || '—'}</dd>
        <dt>État</dt>
        <dd>
          {CONDITION_LABELS[draft.condition_type]}
          {draft.grade && !isNew(draft) ? `, note ${draft.grade}` : ''}
        </dd>
        <dt>Prix</dt>
        <dd>{draft.price_fcfa ? formatFCFA(Number(draft.price_fcfa)) : '—'}</dd>
        <dt>Ville</dt>
        <dd>{draft.city || '—'}</dd>
        <dt>Photos</dt>
        <dd>{photos.length}</dd>
      </dl>
      {missing.length > 0 && (
        <div className={styles.todo} role="alert">
          <p>À corriger avant de publier :</p>
          <ul>
            {missing.map(([k, m]) => (
              <li key={k}>{m}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
