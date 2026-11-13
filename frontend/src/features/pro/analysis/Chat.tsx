import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { Input } from '@/components/Input/Input'
import { ApiError, api } from '@/lib/api'
import type { ChatAnswer } from '../types'
import styles from '../Pro.module.css'

const SUGGESTIONS = [
  'Combien de contacts sur les iPhone ce mois ?',
  'Quelles sont mes annonces les plus vues ?',
  'Compare mes vues avec la semaine dernière',
  'Mes prix sont-ils trop élevés ?',
  'Quelle est la demande pour le MacBook ?',
]

type Turn =
  { question: string; answer: string; usedAi: boolean } | { question: string; error: string }

/** P5: questions answered from the shop's own figures, through predefined functions only. */
export default function Chat() {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const ask = useMutation({
    mutationFn: (q: string) =>
      api<ChatAnswer>('insights/chat/', { method: 'POST', body: { question: q } }),
    onSuccess: (res, q) =>
      setTurns((t) => [...t, { question: q, answer: res.answer, usedAi: res.used_ai }]),
    onError: (e, q) =>
      setTurns((t) => [
        ...t,
        { question: q, error: e instanceof ApiError ? e.message : 'Réponse impossible.' },
      ]),
  })

  function send(q: string) {
    const text = q.trim()
    if (text.length < 3 || ask.isPending) return
    setQuestion('')
    ask.mutate(text)
  }
  function submit(e: FormEvent) {
    e.preventDefault()
    send(question)
  }

  return (
    <section className={styles.page} aria-labelledby="chat-title">
      <div>
        <h2 id="chat-title" className={styles.h2}>
          Discuter avec vos chiffres
        </h2>
        <p className={styles.hint}>
          Posez une question sur les vues, les contacts, les favoris, les ventes, vos prix ou la
          demande. Les réponses ne portent que sur votre boutique.
        </p>
      </div>
      <ul className={styles.suggestions} aria-label="Exemples de questions">
        {SUGGESTIONS.map((s) => (
          <li key={s}>
            <button type="button" onClick={() => send(s)} disabled={ask.isPending}>
              {s}
            </button>
          </li>
        ))}
      </ul>
      <div className={styles.chat} aria-live="polite">
        {turns.map((t, i) => (
          <div key={i} className={styles.chat}>
            <p className={styles.question}>{t.question}</p>
            <div className={styles.answer} role="status">
              {'error' in t ? (
                t.error
              ) : (
                <>
                  <p className={styles.text}>{t.answer}</p>
                  <p className={styles.note}>
                    {t.usedAi
                      ? 'Réponse de l’IA à partir de vos chiffres.'
                      : 'Calculé à partir de vos chiffres.'}
                  </p>
                </>
              )}
            </div>
          </div>
        ))}
        {ask.isPending && <p className={styles.note}>Calcul en cours…</p>}
      </div>
      <form className={styles.form} onSubmit={submit} noValidate>
        <Input
          label="Votre question"
          value={question}
          maxLength={300}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <Button type="submit" disabled={ask.isPending || question.trim().length < 3}>
          Envoyer
        </Button>
      </form>
    </section>
  )
}
