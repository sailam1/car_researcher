import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { API_BASE_URL } from '../../api/config'
import {
  createSession,
  getSession,
  sendChatStream,
  type ChatStreamEvent,
} from '../../api/client'
import { useBackendReady } from '../../context/BackendReadyContext'
import { useSessionStore } from '../../store/sessionStore'
import type { ChatMessage, DiscoveryPhase, UIState } from '../../types'
import './ChatPanel.css'

const PHASE_LABELS: Record<string, string> = {
  welcome: 'Getting started',
  broad: 'Exploring your needs',
  narrow: 'Narrowing options',
  refining: 'Refining shortlist',
  shortlisted: 'Shortlist ready',
  done: 'Ready to compare',
}

export function ChatPanel() {
  const [input, setInput] = useState('')
  const [initError, setInitError] = useState<string | null>(null)
  const [streamStep, setStreamStep] = useState<string | null>(null)
  const [streamingReply, setStreamingReply] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const initStartedRef = useRef(false)
  const {
    sessionId,
    messages,
    discoveryPhase,
    loading,
    setSession,
    setMessages,
    setUiState,
    setPhase,
    setLoading,
  } = useSessionStore()
  const { ready: backendReady, waking: backendWaking } = useBackendReady()

  useEffect(() => {
    if (!backendReady) return

    async function init() {
      const saved = sessionStorage.getItem('cardeko_session_id')
      setLoading(true)
      setInitError(null)
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 30_000)
      try {
        if (saved) {
          try {
            const s = await getSession(saved)
            setSession(s.session_id, s.messages, s.ui_state, s.discovery_phase)
            return
          } catch {
            sessionStorage.removeItem('cardeko_session_id')
          }
        }
        const s = await createSession(controller.signal)
        sessionStorage.setItem('cardeko_session_id', s.session_id)
        setSession(s.session_id, s.messages, s.ui_state, s.discovery_phase)
      } catch (e) {
        const backendHint = API_BASE_URL
          ? API_BASE_URL
          : 'the backend (uvicorn on port 4000)'
        const msg =
          e instanceof Error && e.name === 'AbortError'
            ? `Request timed out. Is ${backendHint} reachable?`
            : `Could not reach the server at ${backendHint}.`
        setInitError(msg)
      } finally {
        window.clearTimeout(timeout)
        setLoading(false)
      }
    }
    if (!sessionId && !initStartedRef.current) {
      initStartedRef.current = true
      void init()
    }
  }, [backendReady, sessionId, setSession, setLoading])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingReply, streamStep])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!input.trim() || !sessionId || loading) return
    const text = input.trim()
    setInput('')
    const optimistic: ChatMessage[] = [
      ...messages,
      { role: 'user', content: text },
    ]
    setMessages(optimistic)
    setLoading(true)
    setStreamStep('Starting…')
    setStreamingReply('')

    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 300_000)

    try {
      await sendChatStream(
        sessionId,
        text,
        (event: ChatStreamEvent) => {
          if (event.type === 'step') {
            setStreamStep(event.label)
          } else if (event.type === 'ui_update') {
            setUiState(event.ui_state)
            setPhase(event.discovery_phase as DiscoveryPhase)
            if (event.shortlist_label) {
              setStreamStep(event.shortlist_label)
            }
          } else if (event.type === 'token') {
            setStreamingReply((prev) => prev + event.content)
          } else if (event.type === 'done') {
            setMessages(event.messages as ChatMessage[])
            setUiState(event.ui_state as UIState)
            setPhase(event.discovery_phase as DiscoveryPhase)
            setStreamingReply('')
            setStreamStep(null)
          } else if (event.type === 'error') {
            throw new Error(event.detail)
          }
        },
        controller.signal
      )
    } catch (err) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Something went wrong. Check the backend terminal.'
      setMessages([
        ...optimistic,
        { role: 'assistant', content: msg },
      ])
      setStreamingReply('')
      setStreamStep(null)
    } finally {
      window.clearTimeout(timeout)
      setLoading(false)
    }
  }

  const showStreaming = loading && (streamStep || streamingReply)

  return (
    <div className="chat-panel">
      <header className="chat-header">
        <h2>Research assistant</h2>
        <span className="phase-badge">
          {PHASE_LABELS[discoveryPhase] ?? discoveryPhase}
        </span>
      </header>
      <div className="chat-messages">
        {backendWaking && messages.length === 0 && (
          <div className="chat-bubble assistant">
            Waiting for the API to wake up on Render (about 1 minute)…
          </div>
        )}
        {backendReady && loading && messages.length === 0 && !initError && (
          <div className="chat-bubble assistant">
            Loading catalog and assistant…
          </div>
        )}
        {initError && (
          <div className="chat-bubble assistant error">{initError}</div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role}`}>
            {m.content}
          </div>
        ))}
        {showStreaming && (
          <div className="chat-bubble assistant typing">
            {streamStep && (
              <div className="stream-step">{streamStep}</div>
            )}
            {streamingReply ? (
              <div className="stream-text">{streamingReply}</div>
            ) : !streamStep ? (
              <span>Thinking…</span>
            ) : null}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input-row" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe what you're looking for…"
          disabled={!backendReady || !sessionId || loading}
        />
        <button
          type="submit"
          disabled={!backendReady || !sessionId || loading || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  )
}
