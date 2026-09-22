import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

export default function DashboardTabs() {
  const location = useLocation()
  const isForecast = location.pathname.startsWith('/dashboard/forecast')

  return (
    <div className="dashboard-tabbed-container">
      <div className="dashboard-tab-content">
        <Outlet />
      </div>
    </div>
  )
}
