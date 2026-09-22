import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { documentsMock } from '../data/documentsMock'
import { reportsMock } from '../data/reportsMock'
import { mockNotifications } from '../data/mockNotifications'
import { mockPastQueries } from '../data/mockPastQueries'

function SearchIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="8.5" cy="8.5" r="5.2" />
      <path d="M13 13l4 4" />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10 3.2a3.5 3.5 0 0 1 3.5 3.5v2.3c0 1.8.7 2.9 1.7 3.7l.8.7H3.9l.8-.7c1-.8 1.7-1.9 1.7-3.7V6.7A3.5 3.5 0 0 1 10 3.2Z" />
      <path d="M8.2 14.8A2 2 0 0 0 10 16a2 2 0 0 0 1.8-1.2" />
    </svg>
  )
}

export default function TopBar({ onMenuToggle }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [notificationList, setNotificationList] = useState(mockNotifications)

  const unreadCount = useMemo(
    () => notificationList.filter((item) => item.unread).length,
    [notificationList],
  )

  const handleNotificationClick = (item) => {
    setNotificationList((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, unread: false } : n)),
    )
    setNotificationsOpen(false)
    if (item.route) {
      navigate(item.route)
    }
  }

  const handleMarkAllRead = () => {
    setNotificationList((prev) => prev.map((n) => ({ ...n, unread: false })))
  }

  const results = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase()

    if (!normalizedQuery) {
      return []
    }

    const documentResults = documentsMock
      .filter((document) => [document.title, document.id, document.subsidiary, document.type].join(' ').toLowerCase().includes(normalizedQuery))
      .map((document) => ({
        id: document.id,
        title: document.title,
        subtitle: `${document.subsidiary} · ${document.status}`,
        kind: 'document',
      }))

    const reportResults = Object.entries(reportsMock['2025-26'])
      .filter(([subsidiary]) => subsidiary.toLowerCase().includes(normalizedQuery))
      .map(([subsidiary]) => ({
        id: subsidiary,
        title: `${subsidiary} FY 2025-26 Report`,
        subtitle: 'Portfolio performance summary',
        kind: 'report',
      }))

    const queryResults = mockPastQueries
      .filter((q) => [q.title, q.queryText, q.category].join(' ').toLowerCase().includes(normalizedQuery))
      .map((q) => ({
        id: q.id,
        title: q.title,
        subtitle: q.subtitle,
        queryText: q.queryText,
        kind: 'ai-query',
        isDemoData: q.isDemoData,
      }))

    return [...queryResults, ...documentResults, ...reportResults].slice(0, 8)
  }, [query])

  const handleSelectResult = (item) => {
    setQuery('')

    if (item.kind === 'ai-query') {
      navigate('/ai-intelligence', { state: { initialQuery: item.queryText } })
      return
    }

    if (item.kind === 'document') {
      navigate(`/documents/${item.id}`)
      return
    }

    navigate('/reports')
  }

  return (
    <header className="topbar">
      <button type="button" className="topbar__menu-toggle" aria-label="Toggle navigation menu" onClick={onMenuToggle}>
        <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <path d="M3 5.5h14M3 10h14M3 14.5h14" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      </button>

      <div className="topbar__search-wrap">
        <div className="topbar__search">
          <span aria-hidden="true" className="topbar__search-icon"><SearchIcon /></span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search reports, mines, documents..."
            aria-label="Global search"
          />
        </div>

        {query && (
          <div className="topbar__search-results" role="listbox" aria-label="Search results">
            {results.length ? (
              results.map((item) => (
                <button key={`${item.kind}-${item.id}`} type="button" className="topbar__result" onClick={() => handleSelectResult(item)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{item.title}</strong>
                    {item.isDemoData && (
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 800,
                          padding: '2px 6px',
                          borderRadius: '3px',
                          background: 'var(--purple-100)',
                          color: 'var(--purple-500)',
                          border: '1px solid var(--tone-ai-border)',
                        }}
                      >
                        DEMO QUERY
                      </span>
                    )}
                  </div>
                  <span>{item.subtitle}</span>
                </button>
              ))
            ) : (
              <div className="topbar__no-results">No matching records found.</div>
            )}
          </div>
        )}
      </div>

      <div className="topbar__actions">
        <div className="topbar__notification-wrap">
          <button type="button" className="topbar__icon" aria-label="Notifications" onClick={() => setNotificationsOpen((state) => !state)}>
            <BellIcon />
            {unreadCount > 0 && <span className="topbar__badge">{unreadCount}</span>}
          </button>

          {notificationsOpen && (
            <div
              className="topbar__notification-panel"
              role="dialog"
              aria-label="Notification center"
              style={{ width: '320px', padding: '12px' }}
            >
              <div
                style={{
                  display: 'flex',
                  justify: 'space-between',
                  alignItems: 'center',
                  paddingBottom: '8px',
                  marginBottom: '8px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--navy-900)' }}>
                  Notifications {unreadCount > 0 && `(${unreadCount})`}
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={handleMarkAllRead}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--steel-700)',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    Mark all as read
                  </button>
                )}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '320px', overflowY: 'auto' }}>
                {notificationList.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => handleNotificationClick(item)}
                    className="topbar__notification-item"
                    style={{
                      padding: '10px',
                      borderRadius: 'var(--radius-sm)',
                      background: item.unread ? 'var(--tone-neutral-soft)' : 'transparent',
                      borderLeft: item.unread ? '3px solid var(--steel-700)' : '3px solid transparent',
                      cursor: 'pointer',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                      <span style={{ fontSize: '12px', fontWeight: item.unread ? 800 : 700, color: 'var(--navy-900)' }}>
                        {item.title}
                      </span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{item.timestamp}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                      {item.detail}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {user ? (
          <div className="topbar__profile" style={{ gap: '12px' }}>
            <div className="topbar__avatar">{user.avatar}</div>
            <div className="topbar__profile-copy">
              <div className="topbar__name">{user.name}</div>
              <div className="topbar__role" style={{ color: 'var(--steel-700)', fontWeight: 700 }}>
                {user.role} • {user.subsidiary}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </header>
  )
}
