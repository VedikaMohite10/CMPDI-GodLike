import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import Tabs from '../components/ui/Tabs'
import DataQualityDashboard from '../components/governance/DataQualityDashboard'
import AuditLogTable from '../components/governance/AuditLogTable'
import UserManagementTable from '../components/governance/UserManagementTable'
import {
  governanceAuditLogsMock,
  governanceDataQualityMock,
  governanceUsersMock,
} from '../data/governanceMock'

const TABS = [
  { id: 'queue', label: 'Review Queue', path: '/data-quality' },
  { id: 'metrics', label: 'Quality Metrics', path: '/data-quality/metrics' },
  { id: 'audit', label: 'Audit Logs', path: '/data-quality/audit' },
  { id: 'admin', label: 'User Management', path: '/data-quality/admin' },
]

export function QualityMetricsView() {
  return <DataQualityDashboard metrics={governanceDataQualityMock} />
}

export function AuditLogsView() {
  return <AuditLogTable logs={governanceAuditLogsMock} />
}

export function UserAdminView() {
  return <UserManagementTable users={governanceUsersMock} />
}

export default function DataQualityTabs() {
  const location = useLocation()
  const navigate = useNavigate()

  let currentTab = 'Review Queue'
  if (location.pathname.startsWith('/data-quality/metrics')) {
    currentTab = 'Quality Metrics'
  } else if (location.pathname.startsWith('/data-quality/audit')) {
    currentTab = 'Audit Logs'
  } else if (location.pathname.startsWith('/data-quality/admin')) {
    currentTab = 'User Management'
  }

  const handleTabChange = (label) => {
    const target = TABS.find((t) => t.label === label)
    if (target && target.path !== location.pathname) {
      navigate(target.path)
    }
  }

  return (
    <div className="tabbed-page-container">
      <div className="page-header">
        <div>
          <p className="eyebrow">Data Governance & Assurance</p>
          <h1>Data Quality & Governance</h1>
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
