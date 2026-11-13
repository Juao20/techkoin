import { Microphone, Stop } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/Button/Button'
import { type VoiceResult, useAiStatus } from '@/lib/ai'
import { ApiError, api } from '@/lib/api'
import styles from './VoiceRecorder.module.css'

const MAX_SECONDS = 60

type Props = { onResult: (result: Extract<VoiceResult, { available: true }>) => void }

/** « Dictée »: the seller describes the device, the form is pre-filled and then checked. */
export function VoiceRecorder({ onResult }: Props) {
  const status = useAiStatus()
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const recorder = useRef<MediaRecorder | null>(null)
  const chunks = useRef<Blob[]>([])
  const timer = useRef<number | null>(null)
  const started = useRef(0)

  useEffect(
    () => () => {
      if (timer.current) window.clearInterval(timer.current)
      recorder.current?.stream.getTracks().forEach((t) => t.stop())
    },
    [],
  )

  if (!status.data?.voice_available || typeof MediaRecorder === 'undefined') return null

  async function upload(blob: Blob, duration: number) {
    setBusy(true)
    setMessage('')
    try {
      const form = new FormData()
      form.append('audio', blob, 'dictee.webm')
      form.append('duration', String(Math.min(duration, MAX_SECONDS)))
      const result = await api<VoiceResult>('ai/voice/', { method: 'POST', form })
      if (!result.available) setMessage('La dictée n’est pas disponible pour le moment.')
      else onResult(result)
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'La dictée n’a pas abouti.')
    } finally {
      setBusy(false)
    }
  }

  async function start() {
    setMessage('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunks.current = []
      rec.ondataavailable = (e) => chunks.current.push(e.data)
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const duration = (Date.now() - started.current) / 1000
        void upload(new Blob(chunks.current, { type: rec.mimeType || 'audio/webm' }), duration)
      }
      recorder.current = rec
      started.current = Date.now()
      rec.start()
      setRecording(true)
      setSeconds(0)
      timer.current = window.setInterval(() => {
        const elapsed = Math.round((Date.now() - started.current) / 1000)
        setSeconds(elapsed)
        if (elapsed >= MAX_SECONDS) stop()
      }, 500)
    } catch {
      setMessage('Autorisez le micro pour dicter, ou saisissez à la main.')
    }
  }

  function stop() {
    if (timer.current) window.clearInterval(timer.current)
    setRecording(false)
    recorder.current?.stop()
  }

  return (
    <div className={styles.wrap}>
      {recording ? (
        <Button variant="danger" onClick={stop}>
          <Stop size={18} weight="fill" aria-hidden /> Arrêter ({seconds}/{MAX_SECONDS} s)
        </Button>
      ) : (
        <Button variant="secondary" onClick={() => void start()} disabled={busy}>
          <Microphone size={18} aria-hidden /> {busy ? 'Analyse…' : 'Dicter la description'}
        </Button>
      )}
      <p className={styles.hint}>
        Par exemple : « iPhone 12, 128 giga, batterie 84, petite rayure derrière, avec chargeur ».
        L’enregistrement est supprimé après l’analyse.
      </p>
      {message && (
        <p className={styles.error} role="alert">
          {message}
        </p>
      )}
    </div>
  )
}
