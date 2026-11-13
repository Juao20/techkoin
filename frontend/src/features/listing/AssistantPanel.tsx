import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Button } from '@/components/Button/Button'
import { useToast } from '@/components/Toast/Toast'
import { useAuth } from '@/features/auth/AuthContext'
import { AUTO_NOTICE, type AssistantAnswer } from '@/lib/ai'
import { ApiError, api } from '@/lib/api'
import type { ListingDetailApi } from '@/lib/types'
import styles from './AssistantPanel.module.css'

const SUGGESTIONS: Record<string, string[]> = {
  laptop: [
    'Ça suffit pour le montage vidéo ?',
    'Quelle est l’autonomie ?',
    'Est-ce une bonne affaire ?',
  ],
  desktop: [
    'Ça suffit pour les jeux ?',
    'Quelle est la mémoire vive ?',
    'Est-ce une bonne affaire ?',
  ],
  smartphone: [
    'La batterie tient combien ?',
    'Des pièces ont été remplacées ?',
    'Est-ce une bonne affaire ?',
  ],
  tablet: ['La batterie tient combien ?', 'Y a-t-il une garantie ?', 'Est-ce une bonne affaire ?'],
}

type Turn = { question: string; answer: AssistantAnswer }

/** « Assistant » on every listing: answers come from the listing's data only. */
export function AssistantPanel({ listing }: { listing: ListingDetailApi }) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { notify } = useToast()
  const [text, setText] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])

  const ask = useMutation({
    mutationFn: (question: string) =>
      api<AssistantAnswer>('ai/assistant/', {
        method: 'POST',
        body: {
          listing_id: listing.id,
          question,
          history: turns.slice(-5).map((t) => t.question),
        },
      }),
    onSuccess: (answer, question) => {
      setTurns((t) => [...t, { question, answer }])
      setText('')
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'L’assistant n’a pas répondu.'),
  })

  const toSeller = useMutation({
    mutationFn: (message: string) =>
      api<{ url: string }>(`listings/${listing.id}/whatsapp/`, {
        method: 'POST',
        body: { message },
      }),
    onSuccess: ({ url }) => window.open(url, '_blank', 'noopener'),
    onError: (e) => notify(e instanceof ApiError ? e.message : 'Impossible d’ouvrir WhatsApp.'),
  })

  function submit(e: FormEvent) {
    e.preventDefault()
    const q = text.trim()
    if (q.length >= 3) ask.mutate(q)
  }

  function contactSeller(message: string) {
    if (!user) {
      navigate('/connexion', { state: { from: location.pathname } })
      return
    }
    toSeller.mutate(message)
  }

  return (
    <section className={styles.wrap} aria-labelledby="assistant-title">
      <h2 id="assistant-title" className={styles.title}>
        Poser une question sur cette annonce
      </h2>
      <ul className={styles.turns} aria-live="polite">
        {turns.map((t, i) => (
          <li key={i} className={styles.turn}>
            <p className={styles.question}>{t.question}</p>
            <p className={styles.answer}>{t.answer.answer}</p>
            {t.answer.information_missing && t.answer.suggested_seller_question && (
              <Button
                variant="secondary"
                disabled={toSeller.isPending}
                onClick={() => contactSeller(t.answer.suggested_seller_question ?? '')}
              >
                Poser la question au vendeur sur WhatsApp
              </Button>
            )}
            {t.answer.used_ai && <p className={styles.notice}>{AUTO_NOTICE}</p>}
          </li>
        ))}
      </ul>
      {turns.length === 0 && (
        <div className={styles.suggestions}>
          {(SUGGESTIONS[listing.category] ?? []).map((s) => (
            <button key={s} type="button" disabled={ask.isPending} onClick={() => ask.mutate(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
      <form onSubmit={submit} className={styles.form}>
        <label htmlFor="assistant-input" className={styles.srOnly}>
          Votre question
        </label>
        <input
          id="assistant-input"
          className={styles.input}
          value={text}
          maxLength={300}
          onChange={(e) => setText(e.target.value)}
          placeholder="Votre question"
        />
        <Button type="submit" disabled={ask.isPending || text.trim().length < 3}>
          {ask.isPending ? 'Réponse…' : 'Demander'}
        </Button>
      </form>
    </section>
  )
}
