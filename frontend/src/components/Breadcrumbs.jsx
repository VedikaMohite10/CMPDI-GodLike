import { Link, useLocation } from 'react-router-dom'

const routeLabels = {
  '/dashboard': 'Dashboard',
  '/dashboard/forecast': 'Forecast',
  '/documents': 'Documents',
  '/ai-intelligence': 'AI Intelligence',
  '/ai-intelligence/topics': 'Topics',
  '/reports': 'Reports',
  '/reports/parliamentary': 'Parliamentary Workflow',
  '/mining-map': 'Mining Map',
  '/data-quality': 'Data Quality',
  '/data-quality/metrics': 'Metrics',
  '/data-quality/audit': 'Audit Trail',
  '/data-quality/admin': 'Administration',
  '/design-system': 'Design System',
}

export default function Breadcrumbs() {
  const location = useLocation()
  const segments = location.pathname.split('/').filter(Boolean)
  const items = segments.map((segment, index) => {
    const path = `/${segments.slice(0, index + 1).join('/')}`

    return {
      label: routeLabels[path] || segment,
      path,
    }
  })

  const breadcrumbs = [{ label: 'Home', path: '/dashboard' }, ...items].filter(
    (item, index, arr) => arr.findIndex((candidate) => candidate.path === item.path) === index,
  )

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      {breadcrumbs.map((item, index) => (
        <span key={`${item.path}-${index}`} className="breadcrumb-item">
          {index < breadcrumbs.length - 1 ? (
            <Link to={item.path}>{item.label}</Link>
          ) : (
            <span>{item.label}</span>
          )}
          {index < breadcrumbs.length - 1 ? <span className="breadcrumb-separator">/</span> : null}
        </span>
      ))}
    </nav>
  )
}
