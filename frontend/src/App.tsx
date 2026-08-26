import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/auth'
import { ToastProvider } from '@/components/ui/Toast'
import AppLayout from '@/components/layout/AppLayout'
import CompanyLayout from '@/components/layout/CompanyLayout'
import Landing from '@/pages/landing/Landing'
import Login from '@/pages/auth/Login'
import Register from '@/pages/auth/Register'
import Dashboard from '@/pages/dashboard/Dashboard'
import Companies from '@/pages/companies/Companies'
import CompanyDetail from '@/pages/companies/CompanyDetail'
import Applications from '@/pages/applications/Applications'
import NewApplication from '@/pages/applications/NewApplication'
import ApplicationDetail from '@/pages/applications/ApplicationDetail'
import RuleEngine from '@/pages/rules/RuleEngine'
import MLModels from '@/pages/predictions/MLModels'
import Analytics from '@/pages/analytics/Analytics'
import Pipeline from '@/pages/pipeline/Pipeline'
import Settings from '@/pages/settings/Settings'
import PortalDashboard from '@/pages/portal/PortalDashboard'
import PortalApplications from '@/pages/portal/PortalApplications'
import PortalApplicationDetail from '@/pages/portal/PortalApplicationDetail'
import PortalCompany from '@/pages/portal/PortalCompany'
import PortalDocuments from '@/pages/portal/PortalDocuments'
import PortalAnnualReport from '@/pages/portal/PortalAnnualReport'

function AppInitializer() {
  const { initialize, initialized } = useAuthStore()
  useEffect(() => { initialize() }, [initialize])
  if (!initialized) return null
  return null
}

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <AppInitializer />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Company portal routes */}
          <Route element={<CompanyLayout />}>
            <Route path="/portal"                    element={<PortalDashboard />} />
            <Route path="/portal/applications"       element={<PortalApplications />} />
            <Route path="/portal/applications/:id"   element={<PortalApplicationDetail />} />
            <Route path="/portal/documents"          element={<PortalDocuments />} />
            <Route path="/portal/annual-report"      element={<PortalAnnualReport />} />
            <Route path="/portal/company"            element={<PortalCompany />} />
          </Route>

          {/* Bank staff + admin routes */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard"              element={<Dashboard />} />
            <Route path="/companies"              element={<Companies />} />
            <Route path="/companies/:id"          element={<CompanyDetail />} />
            <Route path="/applications"           element={<Applications />} />
            <Route path="/applications/new"       element={<NewApplication />} />
            <Route path="/applications/:id"       element={<ApplicationDetail />} />
            <Route path="/rules"                  element={<RuleEngine />} />
            <Route path="/predictions"            element={<MLModels />} />
            <Route path="/analytics"              element={<Analytics />} />
            <Route path="/pipeline"               element={<Pipeline />} />
            <Route path="/settings"               element={<Settings />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
