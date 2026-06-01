import { BackendWakeBanner } from '../components/BackendWakeBanner'
import { ChatPanel } from '../components/chat-panel/ChatPanel'
import { UiUpdater } from '../components/ui-updater/UiUpdater'
import { BackendReadyProvider, useBackendReady } from '../context/BackendReadyContext'
import './ResearchPage.css'

function ResearchLayout() {
  const { ready, waking } = useBackendReady()

  return (
    <div className={`research-page ${waking ? 'research-page--waking' : ''}`}>
      <BackendWakeBanner />
      <div
        className={`research-layout ${!ready ? 'research-layout--blocked' : ''}`}
        aria-busy={!ready}
      >
        <section className="ui-pane">
          <UiUpdater />
        </section>
        <section className="chat-pane">
          <ChatPanel />
        </section>
      </div>
    </div>
  )
}

export function ResearchPage() {
  return (
    <BackendReadyProvider>
      <ResearchLayout />
    </BackendReadyProvider>
  )
}
