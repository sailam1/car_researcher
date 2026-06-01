import {
  healthUrl,
  isRemoteBackend,
  RENDER_WAKE_MAX_SECONDS,
} from './config'

/** Wait between failed health checks before trying again. */
export const HEALTH_POLL_INTERVAL_MS = 3000
/** Single check may run long while Render boots; retry after interval if it fails. */
export const HEALTH_CHECK_TIMEOUT_MS = 75_000

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

async function pingHealth(signal?: AbortSignal): Promise<boolean> {
  const checkAbort = new AbortController()
  const timeoutId = window.setTimeout(
    () => checkAbort.abort(),
    HEALTH_CHECK_TIMEOUT_MS
  )
  const onParentAbort = () => checkAbort.abort()
  signal?.addEventListener('abort', onParentAbort, { once: true })

  try {
    const res = await fetch(healthUrl(), {
      method: 'GET',
      cache: 'no-store',
      signal: checkAbort.signal,
    })
    if (!res.ok) return false
    const body = (await res.json().catch(() => ({}))) as { status?: string }
    return body.status === 'ok' || res.ok
  } catch {
    return false
  } finally {
    window.clearTimeout(timeoutId)
    signal?.removeEventListener('abort', onParentAbort)
  }
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

  while (Date.now() - started < maxWaitMs) {
    if (options?.signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError')
    }

    attempt += 1
    const elapsedSec = Math.floor((Date.now() - started) / 1000)
    options?.onProgress?.({
      elapsedSec,
      attempt,
      detail: `Health check #${attempt} (every ${HEALTH_POLL_INTERVAL_MS / 1000}s)…`,
    })

    const up = await pingHealth(options?.signal)
    if (up) {
      options?.onProgress?.({
        elapsedSec,
        attempt,
        detail: 'API is awake — loading catalog…',
      })
      return
    }

    if (Date.now() - started >= maxWaitMs) break
    await delay(HEALTH_POLL_INTERVAL_MS, options?.signal)
  }

  throw new DOMException('Backend wake timeout', 'AbortError')
}
