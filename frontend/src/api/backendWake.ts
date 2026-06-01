import { API_PREFIX, IS_REMOTE_API } from './config'

const WAKE_POLL_MS = 3_000
const WAKE_MAX_MS = 90_000
const WAKE_REQUEST_TIMEOUT_MS = 20_000

export const RENDER_WAKE_HINT_SEC = 60

export function healthCheckUrl(): string {
  return `${API_PREFIX}/health`
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
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
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), WAKE_REQUEST_TIMEOUT_MS)
  const onAbort = () => controller.abort()
  signal?.addEventListener('abort', onAbort, { once: true })
  try {
    const res = await fetch(healthCheckUrl(), {
      signal: controller.signal,
      cache: 'no-store',
    })
    if (!res.ok) return false
    const body = (await res.json()) as { status?: string }
    return body?.status === 'ok'
  } catch {
    return false
  } finally {
    window.clearTimeout(timeout)
    signal?.removeEventListener('abort', onAbort)
  }
}

export type WakeProgress = {
  elapsedMs: number
  attempt: number
}

/**
 * Poll until the API responds (Render free tier cold start ~1 min).
 * No-op when using local Vite proxy (instant).
 */
export async function waitForBackendActive(
  onProgress?: (p: WakeProgress) => void,
  signal?: AbortSignal
): Promise<void> {
  if (!IS_REMOTE_API) return

  const started = Date.now()
  let attempt = 0
  while (Date.now() - started < WAKE_MAX_MS) {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    attempt += 1
    onProgress?.({ elapsedMs: Date.now() - started, attempt })
    if (await pingHealth(signal)) return
    await sleep(WAKE_POLL_MS, signal)
  }
  throw new Error(
    `API did not respond within ${Math.round(WAKE_MAX_MS / 1000)}s. Try again in a moment.`
  )
}
