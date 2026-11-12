import { Heart, WhatsappLogo } from '@phosphor-icons/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { EmptyState } from '@/components/EmptyState/EmptyState'
import { GradeMark } from '@/components/GradeMark/GradeMark'
import { ListingCard } from '@/components/ListingCard/ListingCard'
import { SpecTable } from '@/components/SpecTable/SpecTable'
import { Tag } from '@/components/Tag/Tag'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { ApiError, api } from '@/lib/api'
import { formatFCFA } from '@/lib/format'
import { timeAgo, toCard } from '@/lib/listings'
import type { ListingCardApi, ListingDetailApi } from '@/lib/types'
import { buildSpecGroups } from './specs'
import styles from './ListingPage.module.css'

const BADGES = {
  good_deal: { tone: 'yellow', label: 'Bonne affaire' },
  fair: { tone: 'green', label: 'Prix correct' },
  above_market: { tone: 'red', label: 'Au-dessus du marché' },
} as const

const SAFETY = [
  'Rencontrez le vendeur dans un lieu public, de jour.',
  'Vérifiez l’appareil allumé avant de payer : écran, batterie, ports, réseau.',
  'Ne payez jamais à l’avance, ni par transfert à un inconnu.',
  'Pour un téléphone, contrôlez l’IMEI en composant *#06# et vérifiez que le compte précédent est retiré.',
]

export default function ListingPage() {
  const { slug = '' } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()
  const { notify } = useToast()
  const [photo, setPhoto] = useState(0)
  const [phone, setPhone] = useState<string | null>(null)

  const listing = useQuery({
    queryKey: ['listing', slug],
    queryFn: () => api<ListingDetailApi>(`listings/${slug}/`),
  })
  const similar = useQuery({
    queryKey: ['listing', slug, 'similar'],
    queryFn: () => api<ListingCardApi[]>(`listings/${slug}/similar/`),
    enabled: listing.isSuccess,
  })

  const l = listing.data

  function requireLogin(): boolean {
    if (user) return true
    navigate('/connexion', { state: { from: location.pathname } })
    return false
  }

  const whatsapp = useMutation({
    mutationFn: () => api<{ url: string }>(`listings/${l?.id}/whatsapp/`, { method: 'POST' }),
    onSuccess: ({ url }) => window.open(url, '_blank', 'noopener'),
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Impossible d’ouvrir WhatsApp.'),
  })

  const reveal = useMutation({
    mutationFn: () => api<{ phone: string }>(`listings/${l?.id}/reveal-phone/`, { method: 'POST' }),
    onSuccess: (r) => setPhone(r.phone),
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Numéro indisponible.'),
  })

  const favorite = useMutation({
    mutationFn: (on: boolean) =>
      api(`listings/${l?.id}/favorite/`, { method: on ? 'POST' : 'DELETE' }),
    onSuccess: (_, on) => {
      queryClient.setQueryData<ListingDetailApi>(['listing', slug], (old) =>
        old ? { ...old, favorited: on } : old,
      )
      notify(on ? 'Ajouté à vos favoris.' : 'Retiré de vos favoris.')
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Action impossible.'),
  })

  if (listing.isPending) return <p>Chargement de l’annonce…</p>
  if (listing.isError || !l) {
    return (
      <EmptyState
        title="Annonce introuvable"
        text="Elle a peut-être été vendue ou retirée."
        action={<Link to="/recherche">Voir les autres annonces</Link>}
      />
    )
  }

  const badge = l.price_badge && l.price_badge !== 'unknown' ? BADGES[l.price_badge] : null
  const photos = l.photos
  const current = photos[photo] ?? photos[0]
  const sold = l.status === 'sold'

  return (
    <article className={styles.page}>
      <nav aria-label="Fil d’Ariane" className={styles.crumbs}>
        <Link to="/recherche">Annonces</Link> / <span>{l.brand || l.category}</span>
      </nav>

      <div className={styles.top}>
        <section aria-label="Photos" className={styles.gallery}>
          <div className={styles.main}>
            {current ? (
              <img src={current.image} alt={`${l.title}, photo ${photo + 1}`} />
            ) : (
              <div className={styles.noPhoto}>Pas de photo</div>
            )}
          </div>
          {photos.length > 1 && (
            <ul className={styles.thumbs}>
              {photos.map((p, i) => (
                <li key={p.id}>
                  <button
                    type="button"
                    aria-label={`Photo ${i + 1}`}
                    aria-current={i === photo}
                    onClick={() => setPhoto(i)}
                  >
                    <img src={p.thumb} alt="" loading="lazy" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className={styles.summary}>
          <h1 className={styles.title}>{l.title}</h1>
          <p className={styles.price}>{formatFCFA(l.price_fcfa)}</p>
          <div className={styles.tags}>
            {sold && <Tag tone="red">Vendue</Tag>}
            {badge && <Tag tone={badge.tone}>{badge.label}</Tag>}
            {l.negotiable && <Tag>Négociable</Tag>}
            {l.has_invoice && <Tag>Facture</Tag>}
            {l.warranty_months > 0 && <Tag tone="green">Garantie {l.warranty_months} mois</Tag>}
          </div>
          {l.grade && <GradeMark grade={l.grade} />}
          <p className={styles.meta}>
            {l.city}
            {l.quartier ? `, ${l.quartier}` : ''} · {timeAgo(l.published_at)}
          </p>

          {!sold && (
            <div className={styles.contact}>
              <Button
                size="lg"
                disabled={whatsapp.isPending}
                onClick={() => requireLogin() && whatsapp.mutate()}
              >
                <WhatsappLogo size={22} weight="fill" aria-hidden /> Écrire sur WhatsApp
              </Button>
              {phone ? (
                <a className={styles.phone} href={`tel:${phone}`}>
                  {phone}
                </a>
              ) : (
                <Button
                  size="lg"
                  variant="secondary"
                  disabled={reveal.isPending}
                  onClick={() => requireLogin() && reveal.mutate()}
                >
                  Afficher le numéro
                </Button>
              )}
              <Button
                variant="ghost"
                aria-pressed={l.favorited}
                onClick={() => requireLogin() && favorite.mutate(!l.favorited)}
              >
                <Heart size={20} weight={l.favorited ? 'fill' : 'regular'} aria-hidden />
                {l.favorited ? 'Dans vos favoris' : 'Ajouter aux favoris'}
              </Button>
            </div>
          )}

          <div className={styles.seller}>
            <p className={styles.sellerName}>
              {l.seller.type === 'shop' && l.seller.slug ? (
                <Link to={`/boutique/${l.seller.slug}`}>{l.seller.name}</Link>
              ) : (
                l.seller.name
              )}
            </p>
            <p className={styles.meta}>
              {l.seller.type === 'shop' ? 'Boutique' : 'Particulier'}
              {l.seller.verified ? ' vérifié(e)' : ''} · membre depuis{' '}
              {new Date(l.seller.member_since).getFullYear()}
            </p>
          </div>
        </section>
      </div>

      {l.description && (
        <section className={styles.block}>
          <h2>Description</h2>
          <p className={styles.description}>{l.description}</p>
        </section>
      )}

      <section className={styles.block}>
        <h2>Caractéristiques</h2>
        <SpecTable groups={buildSpecGroups(l)} />
      </section>

      <section className={styles.block}>
        <h2>Acheter en sécurité</h2>
        <ul className={styles.safety}>
          {SAFETY.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        <Link to="/securite">Tous nos conseils de sécurité</Link>
      </section>

      {similar.data && similar.data.length > 0 && (
        <section className={styles.block}>
          <h2>Annonces similaires</h2>
          <ul className={styles.similar}>
            {similar.data.map((s) => (
              <li key={s.id}>
                <ListingCard listing={toCard(s)} />
              </li>
            ))}
          </ul>
        </section>
      )}
    </article>
  )
}
