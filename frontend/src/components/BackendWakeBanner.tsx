import { API_BASE_URL } from '../api/config'
import {
  IS_REMOTE_API,
  RENDER_WAKE_HINT_SEC,
  useBackendReady,
} from '../context/BackendReadyContext'
import './BackendWakeBanner.css'

export function BackendWakeBanner() {
  const { waking, failed, error, elapsedMs, attempt, retry } = useBackendReady()

  if (!IS_REMOTE_API || (!waking && !failed)) return null

  const elapsedSec = Math.max(1, Math.round(elapsedMs / 1000))
  const progressPct = Math.min(
    100,
    Math.round((elapsedMs / (RENDER_WAKE_HINT_SEC * 1000)) * 100)
  )

  return (
    <div
      className={`backend-wake-banner ${failed ? 'failed' : ''}`}
      role="status"
      aria-live="polite"
    >
      <div className="backend-wake-inner">
        {failed ? (
          <>
            <strong>Could not connect to the API</strong>
            <p>{error}</p>
            <p className="backend-wake-hint">
              On Render, the server may need up to ~{RENDER_WAKE_HINT_SEC} seconds
              to wake after inactivity.
            </p>
            <button type="button" className="backend-wake-retry" onClick={retry}>
              Try again
            </button>
          </>
        ) : (
          <>
            <strong>Starting the research API…</strong>
            <p>
              The backend on Render was asleep. It usually takes about{' '}
              <strong>~{RENDER_WAKE_HINT_SEC} seconds</strong> to become active
              after inactivity.
            </p>
            <p className="backend-wake-meta">
              Waiting… {elapsedSec}s
              {attempt > 0 ? ` (check ${attempt})` : ''}
            </p>
            <div className="backend-wake-progress" aria-hidden>
              <div
                className="backend-wake-progress-bar"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {API_BASE_URL ? (
              <p className="backend-wake-host">{API_BASE_URL}</p>
            ) : null}
          </>
        )}
      </div>
    </div>
  )
}
