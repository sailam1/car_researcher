import { create } from 'zustand'
import type { ChatMessage, DiscoveryPhase, UIState } from '../types'
import { defaultFilters } from '../api/client'
import { normalizeUiState } from '../utils/vehicle'

interface SessionStore {
  sessionId: string | null
  messages: ChatMessage[]
  uiState: UIState
  discoveryPhase: DiscoveryPhase
  loading: boolean
  compareIds: string[]
  setSession: (
    id: string,
    messages: ChatMessage[],
    ui: UIState,
    phase: DiscoveryPhase
  ) => void
  setMessages: (messages: ChatMessage[]) => void
  setUiState: (ui: UIState) => void
  setPhase: (phase: DiscoveryPhase) => void
  setLoading: (v: boolean) => void
  toggleCompare: (id: string) => void
}

export const useSessionStore = create<SessionStore>((set, get) => ({
  sessionId: null,
  messages: [],
  uiState: { filters: defaultFilters(), vehicles: [] },
  discoveryPhase: 'welcome',
  loading: false,
  compareIds: [],
  setSession: (id, messages, ui, phase) =>
    set({
      sessionId: id,
      messages,
      uiState: normalizeUiState(ui),
      discoveryPhase: phase,
    }),
  setMessages: (messages) => set({ messages }),
  setUiState: (ui) => set({ uiState: normalizeUiState(ui) }),
  setPhase: (phase) => set({ discoveryPhase: phase }),
  setLoading: (loading) => set({ loading }),
  toggleCompare: (id) => {
    const cur = get().compareIds
    if (cur.includes(id)) {
      set({ compareIds: cur.filter((x) => x !== id) })
    } else {
      set({ compareIds: [...cur, id] })
    }
  },
}))
