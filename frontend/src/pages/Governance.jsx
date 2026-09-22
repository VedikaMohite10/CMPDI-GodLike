import { useMemo, useState } from 'react'
import DataQualityDashboard from '../components/governance/DataQualityDashboard'
import AuditLogTable from '../components/governance/AuditLogTable'
import UserManagementTable from '../components/governance/UserManagementTable'
import { governanceAuditLogsMock, governanceDataQualityMock, governanceUsersMock } from '../data/governanceMock'

export default function GovernancePage() {
  const [selectedView, setSelectedView] = useState('quality')

  const tabs = useMemo(
    () => [
      { id: 'quality', label: 'Data quality' },
      { id: 'audit', label: 'Audit logs' },
      { id: 'users', label: 'User management' },
    ],
    [],
  )

  return (
    <div className="governance-page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Governance</p>
          <h1>Operations oversight</h1>
        </div>
      </div>

      <div className="governance-tabbar" role="tablist" aria-label="Governance tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={selectedView === tab.id}
            className={`governance-tab ${selectedView === tab.id ? 'is-active' : ''}`}
            onClick={() => setSelectedView(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {selectedView === 'quality' && <DataQualityDashboard metrics={governanceDataQualityMock} />}
      {selectedView === 'audit' && <AuditLogTable logs={governanceAuditLogsMock} />}
      {selectedView === 'users' && <UserManagementTable users={governanceUsersMock} />}
    </div>
  )
}
