import { ChatPanel } from '../components/chat-panel/ChatPanel'
import { UiUpdater } from '../components/ui-updater/UiUpdater'
import './ResearchPage.css'

export function ResearchPage() {
  return (
    <div className="research-layout">
      <section className="ui-pane">
        <UiUpdater />
      </section>
      <section className="chat-pane">
        <ChatPanel />
      </section>
    </div>
  )
}
