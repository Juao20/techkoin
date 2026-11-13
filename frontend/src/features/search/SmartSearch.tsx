import { X } from '@phosphor-icons/react'
import { useMutation } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Button } from '@/components/Button/Button'
import { ApiError, api } from '@/lib/api'
import { AUTO_NOTICE, type SearchInterpretation } from '@/lib/ai'
import { useToast } from '@/components/Toast/Toast'
import styles from './SmartSearch.module.css'

type Props = {
  /** Called with the URL parameters the sentence was turned into. */
  onApply: (filters: Record<string, string>) => void
  /** Called when a chip is removed, with the URL parameters it stood for. */
  onRemove: (keys: string[]) => void
  initialQuery?: string
  autoRun?: boolean
}

export function runSmartSearch(query: string) {
  return api<SearchInterpretation>('ai/search/', { method: 'POST', body: { query } })
}

/** « Recherche intelligente »: a sentence becomes filters the user can edit one by one. */
export function SmartSearch({ onApply, onRemove, initialQuery = '', autoRun = false }: Props) {
  const { notify } = useToast()
  const [text, setText] = useState(initialQuery)
  const [result, setResult] = useState<SearchInterpretation | null>(null)
  const [removed, setRemoved] = useState<number[]>([])

  const search = useMutation({
    mutationFn: runSmartSearch,
    onSuccess: (data) => {
      setResult(data)
      setRemoved([])
      onApply(data.filters)
    },
    onError: (e) => notify(e instanceof ApiError ? e.message : 'La recherche n’a pas abouti.'),
  })

  const { mutate } = search
  useEffect(() => {
    // Arriving from the home page or the header with a sentence: interpret it once.
    if (autoRun && initialQuery.trim().length >= 2) mutate(initialQuery.trim())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function submit(e: FormEvent) {
    e.preventDefault()
    if (text.trim().length >= 2) search.mutate(text.trim())
  }

  const chips = result?.chips ?? []
  return (
    <section className={styles.wrap} aria-labelledby="smart-title">
      <h2 id="smart-title" className={styles.title}>
        Recherche intelligente
      </h2>
      <form onSubmit={submit} className={styles.form}>
        <label htmlFor="smart-input" className={styles.srOnly}>
          Décrivez ce que vous cherchez
        </label>
        <input
          id="smart-input"
          className={styles.input}
          value={text}
          maxLength={200}
          onChange={(e) => setText(e.target.value)}
          placeholder="Un pc pour coder pas trop cher vers Calavi, max 250k"
        />
        <Button type="submit" disabled={search.isPending || text.trim().length < 2}>
          {search.isPending ? 'Analyse…' : 'Chercher'}
        </Button>
      </form>

      {result && (
        <div className={styles.result} role="status">
          {chips.length > 0 ? (
            <>
              <span className={styles.understood}>Compris :</span>
              <ul className={styles.chips}>
                {chips.map((chip, i) =>
                  removed.includes(i) ? null : (
                    <li key={chip.label} className={styles.chip}>
                      {chip.label}
                      <button
                        type="button"
                        aria-label={`Retirer ${chip.label}`}
                        onClick={() => {
                          setRemoved((r) => [...r, i])
                          onRemove(chip.keys)
                        }}
                      >
                        <X size={14} />
                      </button>
                    </li>
                  ),
                )}
              </ul>
            </>
          ) : (
            <p className={styles.none}>
              Je n’ai rien reconnu. Essayez avec un budget, une ville ou un type d’appareil.
            </p>
          )}
          {result.used_ai && <p className={styles.notice}>{AUTO_NOTICE}</p>}
        </div>
      )}
    </section>
  )
}
