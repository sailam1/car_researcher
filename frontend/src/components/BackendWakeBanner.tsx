import { isRemoteBackend, RENDER_WAKE_MAX_SECONDS } from '../api/config'
import './BackendWakeBanner.css'

interface Props {
  active: boolean
  elapsedSeconds: number
  detail?: string | null
}

export function BackendWakeBanner({ active, elapsedSeconds, detail }: Props) {
  if (!active || !isRemoteBackend()) return null

  const pct = Math.min(
    100,
    Math.round((elapsedSeconds / RENDER_WAKE_MAX_SECONDS) * 100)
  )

  return (
    <div className="backend-wake-banner" role="status" aria-live="polite">
      <div className="backend-wake-banner-inner">
        <strong>Waking up the API on Render</strong>
        <p>
          After inactivity the server sleeps. The first request can take{' '}
          <strong>up to about a minute</strong> — please keep this tab open.
        </p>
        <div className="backend-wake-progress" aria-hidden="true">
          <div
            className="backend-wake-progress-bar"
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className="backend-wake-elapsed">
          Waiting… {elapsedSeconds}s
          {elapsedSeconds >= 45 ? ' (still normal on cold start)' : ''}
        </p>
        {detail ? <p className="backend-wake-detail">{detail}</p> : null}
      </div>
    </div>
  )
}
