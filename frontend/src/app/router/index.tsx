import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { AppLayout } from '../../components/layout/AppLayout'

// Feature pages (lazy loaded)
const LandingPage      = React.lazy(() => import('../../features/auth/LandingPage'))
const LoginPage        = React.lazy(() => import('../../features/auth/LoginPage'))
const Dashboard        = React.lazy(() => import('../../features/dashboard/Dashboard'))
const CopilotPage      = React.lazy(() => import('../../features/copilot/CopilotPage'))
const DocumentsPage    = React.lazy(() => import('../../features/documents/DocumentsPage'))
const DocumentDetail   = React.lazy(() => import('../../features/documents/DocumentDetail'))
const EntitiesPage     = React.lazy(() => import('../../features/entities/EntitiesPage'))
const FactsPage        = React.lazy(() => import('../../features/facts/FactsPage'))
const TopicsPage       = React.lazy(() => import('../../features/facts/TopicsPage'))
const AnalyticsPage    = React.lazy(() => import('../../features/analytics/AnalyticsPage'))
const ForecastingPage  = React.lazy(() => import('../../features/forecasting/ForecastingPage'))
const MapPage          = React.lazy(() => import('../../features/map/MapPage'))
const ConflictsPage    = React.lazy(() => import('../../features/conflicts/ConflictsPage'))
const DuplicatesPage   = React.lazy(() => import('../../features/duplicates/DuplicatesPage'))
const ReviewPage       = React.lazy(() => import('../../features/review/ReviewPage'))
const ParliamentaryPage= React.lazy(() => import('../../features/parliamentary/ParliamentaryPage'))
const AuditPage        = React.lazy(() => import('../../features/audit/AuditPage'))
const ReportsPage      = React.lazy(() => import('../../features/reports/ReportsPage'))
const SearchPage       = React.lazy(() => import('../../features/search/SearchPage'))
const UsersPage        = React.lazy(() => import('../../features/admin/UsersPage'))
const SystemHealthPage = React.lazy(() => import('../../features/admin/SystemHealthPage'))
const UnauthorizedPage = React.lazy(() => import('../../features/auth/UnauthorizedPage'))

// Protected route wrapper
function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { isAuth, user } = useAuthStore()

  if (!isAuth) return <Navigate to="/login" replace />

  if (roles && user && !roles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />
  }

  return <>{children}</>
}

// Loading fallback
function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-sm border-2 border-amber-500/30 border-t-amber-500 animate-spin" />
        <span className="text-coal-400 text-xs font-mono">Loading...</span>
      </div>
    </div>
  )
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <React.Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Public */}
          <Route path="/"     element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/unauthorized" element={<UnauthorizedPage />} />

          {/* Authenticated app */}
          <Route element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }>
            <Route path="/dashboard"    element={<Dashboard />} />
            <Route path="/copilot"      element={<CopilotPage />} />
            <Route path="/search"       element={<SearchPage />} />
            <Route path="/documents"    element={<DocumentsPage />} />
            <Route path="/documents/:id" element={<DocumentDetail />} />
            <Route path="/entities"     element={<EntitiesPage />} />
            <Route path="/facts"        element={<FactsPage />} />
            <Route path="/topics"       element={<TopicsPage />} />
            <Route path="/analytics"    element={<AnalyticsPage />} />
            <Route path="/forecasting"  element={<ForecastingPage />} />
            <Route path="/map"          element={<MapPage />} />
            <Route path="/conflicts"    element={<ConflictsPage />} />
            <Route path="/duplicates"   element={<DuplicatesPage />} />
            <Route path="/reports"      element={<ReportsPage />} />

            {/* Reviewer+ */}
            <Route path="/review" element={
              <ProtectedRoute roles={['reviewer','admin']}>
                <ReviewPage />
              </ProtectedRoute>
            } />
            <Route path="/parliamentary" element={
              <ProtectedRoute roles={['reviewer','admin']}>
                <ParliamentaryPage />
              </ProtectedRoute>
            } />
            <Route path="/audit" element={
              <ProtectedRoute roles={['reviewer','admin']}>
                <AuditPage />
              </ProtectedRoute>
            } />

            {/* Admin only */}
            <Route path="/admin/users" element={
              <ProtectedRoute roles={['admin']}>
                <UsersPage />
              </ProtectedRoute>
            } />
            <Route path="/admin/system" element={
              <ProtectedRoute roles={['admin']}>
                <SystemHealthPage />
              </ProtectedRoute>
            } />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </React.Suspense>
    </BrowserRouter>
  )
}
