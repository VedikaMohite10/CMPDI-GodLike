import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Breadcrumbs from '../components/Breadcrumbs'
import LandingNavigation from '../components/LandingNavigation'
import InstitutionalHeader from '../components/InstitutionalHeader'
import InstitutionalFooter from '../components/InstitutionalFooter'

export default function AppShell() {
  const location = useLocation()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isDesktopCollapsed, setIsDesktopCollapsed] = useState(false)

  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [location.pathname])

  const handleMenuToggle = () => {
    if (window.innerWidth <= 768) {
      setIsMobileMenuOpen((state) => !state)
      return
    }

    setIsDesktopCollapsed((state) => !state)
  }

  if (location.pathname.startsWith('/dashboard')) {
    return (
      <div className="dashboard-shell">
        <Outlet />
      </div>
    )
  }

  if (location.pathname.startsWith('/reports')) {
    return (
      <div className="reports-route-shell">
        <LandingNavigation />
        <main className="reports-route-shell__main">
          <div className="reports-route-shell__container">
            <Breadcrumbs key={location.pathname} />
            <Outlet />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="platform-app-shell">
      <InstitutionalHeader />
      <main className="platform-main-container">
        <Outlet />
      </main>
      <InstitutionalFooter />

    </div>
  )
}
