import {
  healthCheckUrls,
  isRemoteBackend,
  RENDER_WAKE_MAX_SECONDS,
} from './config'

/** Wait between failed health checks before trying again. */
export const HEALTH_POLL_INTERVAL_MS = 3000
/** Per-attempt timeout (liveness should respond in seconds once Render is up). */
export const HEALTH_CHECK_TIMEOUT_MS = 10_000

export interface WakeProgress {
  elapsedSec: number
  attempt: number
  detail: string
}

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const t = window.setTimeout(resolve, ms)
    signal?.addEventListener(
      'abort',
      () => {
        window.clearTimeout(t)
        reject(new DOMException('Aborted', 'AbortError'))
      },
      { once: true }
    )
  })
}

async function pingOneUrl(url: string, signal?: AbortSignal): Promise<boolean> {
  const checkAbort = new AbortController()
  const timeoutId = window.setTimeout(
    () => checkAbort.abort(),
    HEALTH_CHECK_TIMEOUT_MS
  )
  const onParentAbort = () => checkAbort.abort()
  signal?.addEventListener('abort', onParentAbort, { once: true })

  try {
    const res = await fetch(url, {
      method: 'GET',
      mode: 'cors',
      cache: 'no-store',
      signal: checkAbort.signal,
    })
    if (!res.ok) return false
    try {
      const body = (await res.json()) as { status?: string; live?: boolean }
      return body.status === 'ok' || body.live === true
    } catch {
      return true
    }
  } catch {
    return false
  } finally {
    window.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', onParentAbort)
  }
}

async function pingHealth(signal?: AbortSignal): Promise<{ ok: boolean; url?: string }> {
  const urls = healthCheckUrls()
  for (const url of urls) {
    if (await pingOneUrl(url, signal)) {
      return { ok: true, url }
    }
  }
  return { ok: false }
}

/**
 * Poll /health every 3s until Render (or remote API) is up, then resolve.
 * No-op for local dev (Vite proxy).
 */
export async function waitForBackendReady(options?: {
  signal?: AbortSignal
  onProgress?: (progress: WakeProgress) => void
}): Promise<void> {
  if (!isRemoteBackend()) return

  const maxWaitMs = (RENDER_WAKE_MAX_SECONDS + 30) * 1000
  const started = Date.now()
  let attempt = 0
  const urls = healthCheckUrls()

  while (Date.now() - started < maxWaitMs) {
    if (options?.signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    attempt += 1
    const elapsedSec = Math.floor((Date.now() - started) / 1000)
    options?.onProgress?.({
      elapsedSec,
      attempt,
      detail: `Health check #${attempt} → ${urls[0]} (retry every ${HEALTH_POLL_INTERVAL_MS / 1000}s)…`,
    })

    const { ok, url } = await pingHealth(options?.signal)
    if (ok) {
      options?.onProgress?.({
        elapsedSec,
        attempt,
        detail: url
          ? `API is awake (${url}) — loading catalog…`
          : 'API is awake — loading catalog…',
      })
      return
    }

    if (Date.now() - started >= maxWaitMs) break
    await delay(HEALTH_POLL_INTERVAL_MS, options?.signal)
  }

  throw new DOMException('Backend wake timeout', 'AbortError')
}
