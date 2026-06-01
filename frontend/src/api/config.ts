/**
 * API base URL for the Cardeko backend.
 * - Dev (vite): unset → `/api` proxied to localhost:4000
 * - Prod (Netlify): VITE_API_BASE_URL → https://car-researcher.onrender.com/api
 */
const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''

export const API_BASE_URL = raw.replace(/\/$/, '')

/** Prefix for all REST routes, e.g. `/api` or `https://host/api` */
export const API_PREFIX = API_BASE_URL ? `${API_BASE_URL}/api` : '/api'

/** True when UI talks to a remote host (e.g. Render), not Vite-local proxy only. */
export const IS_REMOTE_API = Boolean(API_BASE_URL)
