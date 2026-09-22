import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './layouts/AppShell'

// Tabbed Section Containers
import DashboardTabs from './pages/DashboardTabs'
import AIIntelligenceTabs from './pages/AIIntelligenceTabs'
import ReportsTabs from './pages/ReportsTabs'
import DataQualityTabs, {
  QualityMetricsView,
  AuditLogsView,
  UserAdminView,
} from './pages/DataQualityTabs'

// Core Views
import DashboardPage from './pages/DashboardPage'
import ForecastingPage from './pages/Forecasting'
import DocumentsPage from './pages/Documents'
import DocumentWorkspacePage from './pages/DocumentWorkspace'
import AIQueryPage from './pages/AIQuery'
import TopicIntelligencePage from './pages/TopicIntelligence'
import ReportsPage from './pages/Reports'
import ParliamentaryQueryPage from './pages/ParliamentaryQuery'
import MiningMapPage from './pages/MiningMap'
import VerificationPage from './pages/Verification'
import DesignSystemPage from './pages/DesignSystemPage'
import LandingPage from './pages/LandingPage'
import { AuthProvider } from './context/AuthContext'
import './App.css'

function AppRoutes() {
  return (
    <Routes>
      {/* Standalone Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Internal Application Shell (Direct Access) */}
      <Route element={<AppShell />}>

        {/* 1. Dashboard & Forecasting */}
        <Route path="/dashboard" element={<DashboardTabs />}>
          <Route index element={<DashboardPage hideHeader />} />
          <Route path="forecast" element={<ForecastingPage hideHeader />} />
        </Route>

        {/* 2. Documents & Workspace */}
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentWorkspacePage />} />

        {/* 3. AI Intelligence (Copilot + Topic Intelligence) */}
        <Route path="/ai-intelligence" element={<AIIntelligenceTabs />}>
          <Route index element={<AIQueryPage />} />
          <Route path="topics" element={<TopicIntelligencePage hideHeader />} />
        </Route>

        {/* 4. Reports & Responses (Report Builder + Parliamentary Workflow) */}
        <Route path="/reports" element={<ReportsTabs />}>
          <Route index element={<ReportsPage hideHeader />} />
          <Route path="parliamentary" element={<ParliamentaryQueryPage hideHeader />} />
        </Route>

        {/* 5. Mining Map */}
        <Route path="/mining-map" element={<MiningMapPage />} />

        {/* 6. Data Quality & Operations Governance */}
        <Route path="/data-quality" element={<DataQualityTabs />}>
          <Route index element={<VerificationPage hideHeader />} />
          <Route path="metrics" element={<QualityMetricsView />} />
          <Route path="audit" element={<AuditLogsView />} />
          <Route path="admin" element={<UserAdminView />} />
        </Route>

        {/* Developer Design System Sandbox (preserved, hidden from main navigation) */}
        <Route path="/design-system" element={<DesignSystemPage />} />

        {/* Backward Compatibility Redirects */}
        <Route path="/forecasting" element={<Navigate to="/dashboard/forecast" replace />} />
        <Route path="/ai-query" element={<Navigate to="/ai-intelligence" replace />} />
        <Route path="/topic-intelligence" element={<Navigate to="/ai-intelligence/topics" replace />} />
        <Route path="/parliamentary-query" element={<Navigate to="/reports/parliamentary" replace />} />
        <Route path="/verification" element={<Navigate to="/data-quality" replace />} />
        <Route path="/governance" element={<Navigate to="/data-quality/metrics" replace />} />
        <Route path="/document-workspace" element={<Navigate to="/documents/DOC-CCL-2041" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
