export class ApiError extends Error {
  status: number
  code: string
  fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

function readCookie(name: string): string {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return match ? decodeURIComponent(match.split('=')[1] ?? '') : ''
}

function flattenFields(raw: unknown): Record<string, string> {
  if (!raw || typeof raw !== 'object') return {}
  const out: Record<string, string> = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    out[key] = Array.isArray(value) ? String(value[0] ?? '') : String(value)
  }
  return out
}

let csrfReady: Promise<unknown> | null = null

async function ensureCsrf() {
  if (readCookie('csrftoken')) return
  csrfReady ??= fetch('/api/auth/csrf/', { credentials: 'same-origin' }).finally(() => {
    csrfReady = null
  })
  await csrfReady
}

type Options = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  form?: FormData
  query?: Record<string, string | number | boolean | undefined | null>
  signal?: AbortSignal
}

export function buildQuery(query: Options['query']): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === '') continue
    params.set(key, String(value))
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const method = options.method ?? 'GET'
  const headers: Record<string, string> = { Accept: 'application/json' }
  let body: BodyInit | undefined
  if (method !== 'GET') {
    await ensureCsrf()
    headers['X-CSRFToken'] = readCookie('csrftoken')
  }
  if (options.form) {
    body = options.form
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  let response: Response
  try {
    response = await fetch(`/api/${path}${buildQuery(options.query)}`, {
      method,
      headers,
      body,
      credentials: 'same-origin',
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'network', 'Connexion impossible. Vérifiez votre réseau et réessayez.')
  }

  if (response.status === 204) return undefined as T
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const err = (data ?? {}) as { code?: string; message?: string; fields?: unknown }
    throw new ApiError(
      response.status,
      err.code ?? 'error',
      err.message ?? 'Une erreur est survenue. Réessayez dans un instant.',
      flattenFields(err.fields),
    )
  }
  return data as T
}

/** Fire-and-forget front events (whatsapp_click, compare, ...). Never blocks the UI. */
export function trackEvent(type: string, payload: Record<string, unknown> = {}) {
  void api('events/', { method: 'POST', body: { type, ...payload } }).catch(() => undefined)
}
