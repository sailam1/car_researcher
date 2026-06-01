import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { waitForBackendActive, RENDER_WAKE_HINT_SEC } from '../api/backendWake'
import { IS_REMOTE_API } from '../api/config'

type WakeState = {
  ready: boolean
  waking: boolean
  failed: boolean
  error: string | null
  elapsedMs: number
  attempt: number
  retry: () => void
}

const defaultState: WakeState = {
  ready: true,
  waking: false,
  failed: false,
  error: null,
  elapsedMs: 0,
  attempt: 0,
  retry: () => {},
}

const BackendReadyContext = createContext<WakeState>(defaultState)

export function BackendReadyProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(!IS_REMOTE_API)
  const [waking, setWaking] = useState(IS_REMOTE_API)
  const [failed, setFailed] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [elapsedMs, setElapsedMs] = useState(0)
  const [attempt, setAttempt] = useState(0)
  const [runId, setRunId] = useState(0)

  const retry = useCallback(() => {
    setRunId((n) => n + 1)
  }, [])

  useEffect(() => {
    if (!IS_REMOTE_API) return

    const ac = new AbortController()
    setWaking(true)
    setReady(false)
    setFailed(false)
    setError(null)
    setElapsedMs(0)
    setAttempt(0)

    void (async () => {
      try {
        await waitForBackendActive(
          ({ elapsedMs: ms, attempt: n }) => {
            setElapsedMs(ms)
            setAttempt(n)
          },
          ac.signal
        )
        if (!ac.signal.aborted) {
          setReady(true)
          setWaking(false)
        }
      } catch (e) {
        if (ac.signal.aborted) return
        setFailed(true)
        setWaking(false)
        setError(
          e instanceof Error
            ? e.message
            : 'Could not reach the API. Please try again.'
        )
      }
    })()

    return () => ac.abort()
  }, [runId])

  const value = useMemo(
    () => ({
      ready,
      waking,
      failed,
      error,
      elapsedMs,
      attempt,
      retry,
    }),
    [ready, waking, failed, error, elapsedMs, attempt, retry]
  )

  return (
    <BackendReadyContext.Provider value={value}>
      {children}
    </BackendReadyContext.Provider>
  )
}

export function useBackendReady(): WakeState {
  return useContext(BackendReadyContext)
}

export { RENDER_WAKE_HINT_SEC, IS_REMOTE_API }
