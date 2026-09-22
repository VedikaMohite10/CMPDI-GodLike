import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import Tabs from '../components/ui/Tabs'

const TABS = [
  { id: 'copilot', label: 'Copilot Workspace', path: '/ai-intelligence' },
  { id: 'topics', label: 'Topic Intelligence', path: '/ai-intelligence/topics' },
]

export default function AIIntelligenceTabs() {
  const location = useLocation()
  const navigate = useNavigate()

  const isTopics = location.pathname.startsWith('/ai-intelligence/topics')
  const currentTab = isTopics ? 'Topic Intelligence' : 'Copilot Workspace'

  const handleTabChange = (label) => {
    const target = TABS.find((t) => t.label === label)
    if (target && target.path !== location.pathname) {
      navigate(target.path)
    }
  }

  if (!isTopics) {
    return <Outlet />
  }

  return (
    <div className="tabbed-page-container">
      <div className="page-header">
        <div>
          <p className="eyebrow">Mining Intelligence</p>
          <h1>AI Intelligence & Topic Analytics</h1>
        </div>
      </div>
      <Tabs
        tabs={TABS.map((t) => t.label)}
        value={currentTab}
        onChange={handleTabChange}
      />
      <div className="tab-content">
        <Outlet />
      </div>
    </div>
  )
}
