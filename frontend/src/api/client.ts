import type {
  ActiveFilters,
  ChatResponse,
  CompareVehicle,
  SessionCreateResponse,
  SessionResponse,
  UIState,
  VehicleCard,
} from '../types'

const API = '/api'

export async function createSession(
  signal?: AbortSignal
): Promise<SessionCreateResponse> {
  const res = await fetch(`${API}/sessions`, { method: 'POST', signal })
  if (!res.ok) throw new Error(await errorDetail(res))
  return res.json()
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API}/sessions/${sessionId}`)
  if (!res.ok) throw new Error('Session not found')
  return res.json()
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
    }
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status})`
}

export type ChatStreamEvent =
  | { type: 'step'; step: string; label: string }
  | { type: 'ui_update'; ui_state: UIState; discovery_phase: string; shortlist_label?: string; candidate_count?: number }
  | { type: 'token'; content: string }
  | {
      type: 'done'
      reply: string
      messages: ChatResponse['messages']
      ui_state: UIState
      discovery_phase: string
      shortlist_label?: string
      candidate_count?: number
    }
  | { type: 'error'; detail: string }

export async function sendChatStream(
  sessionId: string,
  message: string,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })
  if (!res.ok) throw new Error(await errorDetail(res))
  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      try {
        const event = JSON.parse(line.slice(6)) as ChatStreamEvent
        onEvent(event)
      } catch {
        /* skip malformed */
      }
    }
  }
}

export async function sendChat(
  sessionId: string,
  message: string,
  signal?: AbortSignal
): Promise<ChatResponse> {
  const res = await fetch(`${API}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })
  if (!res.ok) throw new Error(await errorDetail(res))
  return res.json()
}

export async function updateFilters(
  sessionId: string,
  filters: ActiveFilters
): Promise<{
  ui_state: UIState
  discovery_phase: string
  reply?: string
}> {
  const res = await fetch(`${API}/sessions/${sessionId}/filters`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(filters),
  })
  if (!res.ok) throw new Error('Filter update failed')
  return res.json()
}

export async function getVehicle(vehicleId: string) {
  const res = await fetch(`${API}/vehicles/${vehicleId}`)
  if (!res.ok) throw new Error('Vehicle not found')
  return res.json()
}

export async function compareVehicles(
  ids: string[]
): Promise<{ vehicles: CompareVehicle[] }> {
  const res = await fetch(`${API}/compare?ids=${ids.join(',')}`)
  if (!res.ok) throw new Error('Compare failed')
  return res.json()
}

export function placeholderUrl(make: string): string {
  const name = `${make.toUpperCase().replace(/\s+/g, '_')}.png`
  return `${API}/placeholders/${name}`
}

export function defaultFilters(): ActiveFilters {
  return {
    makes: [],
    models: [],
    engine_fuel_types: [],
    gearbox_types: [],
    drivetrains: [],
  }
}

export type { VehicleCard }
