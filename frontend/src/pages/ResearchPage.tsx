import { BackendWakeBanner } from '../components/BackendWakeBanner'
import { ChatPanel } from '../components/chat-panel/ChatPanel'
import { UiUpdater } from '../components/ui-updater/UiUpdater'
import { useSessionStore } from '../store/sessionStore'
import './ResearchPage.css'

export function ResearchPage() {
  const { apiWaking, apiWakeElapsedSec, apiWakeDetail } = useSessionStore()

  return (
    <div className="research-page">
      <BackendWakeBanner
        active={apiWaking}
        elapsedSeconds={apiWakeElapsedSec}
        detail={apiWakeDetail}
      />
      <div className="research-layout">
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
