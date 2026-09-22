import { NavLink, useLocation } from 'react-router-dom'

const navigationItems = [
  { label: 'Dashboard', path: '/dashboard', icon: 'dashboard' },
  { label: 'Documents', path: '/documents', icon: 'documents' },
  { label: 'AI Intelligence', path: '/ai-intelligence', icon: 'ai' },
  { label: 'Reports & Responses', path: '/reports', icon: 'reports' },
  { label: 'Mining Map', path: '/mining-map', icon: 'map' },
  { label: 'Data Quality', path: '/data-quality', icon: 'verification' },
]

function SidebarIcon({ name }) {
  const commonProps = {
    width: 18,
    height: 18,
    viewBox: '0 0 20 20',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': 'true',
  }

  switch (name) {
    case 'dashboard':
      return (
        <svg {...commonProps}>
          <rect x="3" y="3" width="6" height="5.5" rx="1.5" />
          <rect x="11" y="3" width="6" height="3.5" rx="1.5" />
          <rect x="3" y="11" width="6" height="6" rx="1.5" />
          <rect x="11" y="8.5" width="6" height="8.5" rx="1.5" />
        </svg>
      )
    case 'documents':
      return (
        <svg {...commonProps}>
          <path d="M6 2.8h6l3 3v10.4a1.8 1.8 0 0 1-1.8 1.8H6A1.8 1.8 0 0 1 4.2 16.2V4.6A1.8 1.8 0 0 1 6 2.8Z" />
          <path d="M12 2.8v3.4h3.2" />
          <path d="M7 9.5h6M7 12.8h6" />
        </svg>
      )
    case 'workspace':
      return (
        <svg {...commonProps}>
          <path d="M4 7.2A2.2 2.2 0 0 1 6.2 5h7.6A2.2 2.2 0 0 1 16 7.2v6.6A2.2 2.2 0 0 1 13.8 16H6.2A2.2 2.2 0 0 1 4 13.8V7.2Z" />
          <path d="M8 8.7h4M8 11.4h6" />
        </svg>
      )
    case 'ai':
      return (
        <svg {...commonProps}>
          <path d="M10 3.5c2.2 0 4 1.8 4 4 0 1-.3 1.9-.9 2.7l.8 3.3-3.2-1.7L7.4 13l.9-3.3A4 4 0 0 1 6 7.5c0-2.2 1.8-4 4-4Z" />
          <path d="M9.4 7.7h1.2M10 6.2v2.8" />
        </svg>
      )
    case 'verification':
      return (
        <svg {...commonProps}>
          <path d="M9.8 2.8 5.1 4.5v4.3c0 3 1.8 5.7 4.7 7 2.9-1.3 4.7-4 4.7-7V4.5l-4.7-1.7Z" />
          <path d="m8.2 10.1 1.4 1.4 2.9-3.4" />
        </svg>
      )
    case 'reports':
      return (
        <svg {...commonProps}>
          <path d="M5 15.5V8.8M10 15.5V5.2M15 15.5v-7.5" />
          <path d="M3.2 15.7h13.6" />
        </svg>
      )
    case 'forecast':
      return (
        <svg {...commonProps}>
          <path d="M4 13.3 8 9.3l2.5 2.4 5.4-6.7" />
          <path d="M13.8 5h2.7v2.7" />
          <path d="M3.2 15.5h13.6" />
        </svg>
      )
    case 'topics':
      return (
        <svg {...commonProps}>
          <path d="M8 4.8a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5Zm5 5.6a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5Zm-7.6 1.3h5.6M12.6 7.1l1.6-1.7M10 15.1l-1.5-1.7" />
        </svg>
      )
    case 'map':
      return (
        <svg {...commonProps}>
          <path d="M7.2 3.4 3.4 5v11.6l3.8-1.6 4.6 1.6 4.8-1.6V3.8l-4.8 1.6-4.6-1.9Z" />
          <path d="M7.2 3.4v11.1M12 5v11.1" />
        </svg>
      )
    case 'parliament':
      return (
        <svg {...commonProps}>
          <path d="M5 15.6h10M6.5 15.6V9.3h7v6.3M8 9.3V6.8A2 2 0 0 1 10 4.8a2 2 0 0 1 2 2v2.5" />
          <path d="M9.1 7.8h1.8" />
        </svg>
      )
    case 'governance':
      return (
        <svg {...commonProps}>
          <path d="M10 2.8 15.4 4.8v4.2c0 3.6-2.1 7-5.4 9.1a9.6 9.6 0 0 1-5.4-9.1V4.8L10 2.8Z" />
          <path d="M8.2 10.1 9.6 11.5l2.8-3.3" />
        </svg>
      )
    case 'design':
      return (
        <svg {...commonProps}>
          <path d="M4.6 15.4 9 5l6 10" />
          <path d="M6.1 12.5h5.3" />
          <circle cx="13.7" cy="7.5" r="1.5" />
        </svg>
      )
    default:
      return (
        <svg {...commonProps}>
          <circle cx="10" cy="10" r="5.7" />
        </svg>
      )
  }
}

export default function Sidebar({ isDrawerOpen = false, isCollapsed = false, onClose = () => {} }) {
  const { pathname } = useLocation()

  return (
    <aside className={`app-sidebar ${isDrawerOpen ? 'is-open' : ''} ${isCollapsed ? 'is-collapsed' : ''}`}>
      <div className="sidebar-brand">
        <div className="sidebar-brand__mark">CMP</div>
        <div>
          <div className="sidebar-brand__title">CMPDI / CIL</div>
          <div className="sidebar-brand__subtitle">Mining Intelligence Platform</div>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Main navigation">
        {navigationItems.map((item) => {
          const isActive = pathname === item.path || pathname.startsWith(item.path + '/')

          return (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onClose}
              className={isActive ? 'sidebar-nav__link sidebar-nav__link--active' : 'sidebar-nav__link'}
            >
              <span className="sidebar-nav__icon" aria-hidden="true">
                <SidebarIcon name={item.icon} />
              </span>
              <span className="sidebar-nav__label">{item.label}</span>
            </NavLink>
          )
        })}
      </nav>
    </aside>
  )
}
