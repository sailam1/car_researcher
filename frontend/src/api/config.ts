/**
 * API base URL for the Cardeko backend.
 * - Dev (vite): unset → `/api` proxied to localhost:4000
 * - Prod (Netlify): VITE_API_BASE_URL → https://car-researcher.onrender.com/api
 */
const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''

export const API_BASE_URL = raw.replace(/\/$/, '')

/** Prefix for all REST routes, e.g. `/api` or `https://host/api` */
export const API_PREFIX = API_BASE_URL ? `${API_BASE_URL}/api` : '/api'

/** True when the UI talks to a remote API (e.g. Render), not the Vite dev proxy. */
export function isRemoteBackend(): boolean {
  return Boolean(API_BASE_URL)
}

/** Render free tier cold start — shown while waiting for the first response. */
export const RENDER_WAKE_MAX_SECONDS = 90

export function healthUrl(): string {
  return isRemoteBackend() ? `${API_BASE_URL}/health` : 'http://127.0.0.1:4000/health'
}
