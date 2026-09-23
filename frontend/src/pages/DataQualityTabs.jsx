import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import Tabs from '../components/ui/Tabs'
import DataQualityDashboard from '../components/governance/DataQualityDashboard'
import AuditLogTable from '../components/governance/AuditLogTable'
import UserManagementTable from '../components/governance/UserManagementTable'
import { governanceDataQualityMock } from '../data/governanceMock'
import { useAuth } from '../context/AuthContext'
import { listAuditLog } from '../api/review'
import { apiFetch } from '../api/client'

const TABS = [
  { id: 'queue', label: 'Review Queue', path: '/data-quality' },
  { id: 'metrics', label: 'Quality Metrics', path: '/data-quality/metrics' },
  { id: 'audit', label: 'Audit Logs', path: '/data-quality/audit' },
  { id: 'admin', label: 'User Management', path: '/data-quality/admin' },
]

export function QualityMetricsView() {
  const { token } = useAuth()
  const [metrics, setMetrics] = useState(governanceDataQualityMock)

  useEffect(() => {
    if (!token) return
    apiFetch('/dashboard/stats', { token })
      .then((data) => {
        // Map the nested backend response to the flat shape DataQualityDashboard expects
        setMetrics({
          documentsProcessed:  data.pipeline?.documents_processed  ?? governanceDataQualityMock.documentsProcessed,
          pagesProcessed:      data.pipeline?.pages_processed      ?? governanceDataQualityMock.pagesProcessed,
          tablesExtracted:     data.pipeline?.tables_extracted     ?? governanceDataQualityMock.tablesExtracted,
          extractionAccuracy:  data.extraction?.avg_confidence_pct ?? governanceDataQualityMock.extractionAccuracy,
          lowConfidenceFields: data.extraction?.low_confidence_count ?? governanceDataQualityMock.lowConfidenceFields,
          duplicateDocuments:  data.trust?.duplicate_count         ?? governanceDataQualityMock.duplicateDocuments,
          conflictingValues:   data.trust?.open_conflicts          ?? governanceDataQualityMock.conflictingValues,
          missingData:         data.normalization?.missing_entity_count ?? governanceDataQualityMock.missingData,
          humanCorrections:    data.review?.corrected_facts        ?? governanceDataQualityMock.humanCorrections,
          automationPercent:   data.automation?.automation_pct     ?? governanceDataQualityMock.automationPercent,
          manualTimeReduction: governanceDataQualityMock.manualTimeReduction,
          averageProcessingTime: governanceDataQualityMock.averageProcessingTime,
        })
      })
      .catch(() => { /* keep mock fallback */ })
  }, [token])

  return <DataQualityDashboard metrics={metrics} />
}

/** Normalise backend audit log items to the shape AuditLogTable expects */
function normaliseAuditRow(e) {
  return {
    id:        e.id,
    // Backend AuditLog uses `timestamp` (not `created_at`) and `note` (not `description`)
    timestamp: e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : '—',
    user:      e.reviewer ?? '—',
    action:    e.action_type ?? '—',
    document:  e.target_id ?? '—',
    model:     e.model_used ?? '—',
    result:    e.result ?? e.action_type ?? 'success',
    notes:     e.note ?? e.description ?? '',
  }
}

/** Normalise backend user to the shape UserManagementTable expects */
function normaliseUser(u) {
  return {
    id:          u.id,
    name:        u.username,
    role:        u.role ?? 'analyst',
    team:        u.team ?? '—',
    status:      u.is_active ? 'Active' : 'Inactive',
    lastLogin:   u.last_login ? new Date(u.last_login).toLocaleDateString('en-IN') : '—',
    permissions: u.role === 'admin' ? ['read', 'write', 'admin'] : u.role === 'reviewer' ? ['read', 'write'] : ['read'],
  }
}

export function AuditLogsView() {
  const { token } = useAuth()
  const [logs, setLogs] = useState([])

  useEffect(() => {
    if (!token) return
    listAuditLog(token, { pageSize: 100 })
      .then((r) => setLogs((r.items ?? []).map(normaliseAuditRow)))
      .catch(() => {/* keep empty */})
  }, [token])

  return <AuditLogTable logs={logs} />
}

export function UserAdminView() {
  const { token } = useAuth()
  const [users, setUsers] = useState([])

  useEffect(() => {
    if (!token) return
    apiFetch('/auth/users', { token })
      .then((r) => setUsers((r.items ?? r ?? []).map(normaliseUser)))
      .catch(() => {/* keep empty — endpoint may not exist yet (Phase 6) */})
  }, [token])

  return <UserManagementTable users={users} />
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

