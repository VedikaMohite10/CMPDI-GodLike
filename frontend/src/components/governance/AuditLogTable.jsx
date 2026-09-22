import { useMemo, useState } from 'react'
import Card from '../ui/Card'
import { EmptyState } from '../ui/StatePanel'

export default function AuditLogTable({ logs }) {
  const [userFilter, setUserFilter] = useState('All users')
  const [actionFilter, setActionFilter] = useState('All actions')
  const [resultFilter, setResultFilter] = useState('All results')

  const uniqueUsers = ['All users', ...new Set(logs.map((item) => item.user))]
  const uniqueActions = ['All actions', ...new Set(logs.map((item) => item.action))]
  const uniqueResults = ['All results', ...new Set(logs.map((item) => item.result))]

  const filteredLogs = useMemo(
    () =>
      logs.filter((item) => {
        const matchesUser = userFilter === 'All users' || item.user === userFilter
        const matchesAction = actionFilter === 'All actions' || item.action === actionFilter
        const matchesResult = resultFilter === 'All results' || item.result === resultFilter

        return matchesUser && matchesAction && matchesResult
      }),
    [logs, userFilter, actionFilter, resultFilter],
  )

  return (
    <Card className="governance-card">
      <div className="section-header governance-header-row">
        <div>
          <p className="eyebrow">Audit trail</p>
          <h2>Operational log</h2>
        </div>
      </div>

      <div className="governance-toolbar">
        <select value={userFilter} onChange={(event) => setUserFilter(event.target.value)} className="documents-filter">
          {uniqueUsers.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select value={actionFilter} onChange={(event) => setActionFilter(event.target.value)} className="documents-filter">
          {uniqueActions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select value={resultFilter} onChange={(event) => setResultFilter(event.target.value)} className="documents-filter">
          {uniqueResults.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>

      {filteredLogs.length === 0 ? (
        <EmptyState title="No audit entries match the active filters" description="Try adjusting the user, action, or result filters to widen the selection." />
      ) : (
        <div className="table-wrap">
          <table className="governance-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Document</th>
                <th>Model</th>
                <th>Result</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((entry) => (
                <tr key={entry.id}>
                  <td>{entry.timestamp}</td>
                  <td>{entry.user}</td>
                  <td>{entry.action}</td>
                  <td>{entry.document}</td>
                  <td>{entry.model}</td>
                  <td>
                    <span className={`status-pill status-pill--${entry.result.toLowerCase()}`}>{entry.result}</span>
                  </td>
                  <td>{entry.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
