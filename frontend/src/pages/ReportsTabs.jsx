import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import Tabs from '../components/ui/Tabs'

const TABS = [
  { id: 'parliamentary', label: 'Parliamentary Workflow', path: '/reports/parliamentary' },
  { id: 'builder', label: 'Report Builder', path: '/reports' },
]

export function ReportsTabNavigation() {
  const location = useLocation()
  const navigate = useNavigate()

  const isParliamentary = location.pathname.startsWith('/reports/parliamentary')
  const currentTab = isParliamentary ? 'Parliamentary Workflow' : 'Report Builder'

  const handleTabChange = (label) => {
    const target = TABS.find((t) => t.label === label)
    if (target && target.path !== location.pathname) {
      navigate(target.path)
    }
  }

  return (
      <Tabs
        tabs={TABS.map((t) => t.label)}
        value={currentTab}
        onChange={handleTabChange}
      />
  )
}

export default function ReportsTabs() {
  const location = useLocation()
  const isParliamentary = location.pathname.startsWith('/reports/parliamentary')

  return (
    <div className="tabbed-page-container reports-tab">
      {isParliamentary && (
        <div className="page-header">
          <div>
            <p className="eyebrow">Reports &amp; Analysis</p>
            <h1>Reports &amp; Analysis</h1>
            <p className="reports-header-description">Generate, view and analyze reports across subsidiaries, coalfields, and operational domains.</p>
          </div>
        </div>
      )}
      <ReportsTabNavigation />
      <div className="tab-content">
        <Outlet />
      </div>
    </div>
  )
}
