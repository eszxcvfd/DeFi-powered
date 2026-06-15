import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, type ReactNode } from "react";
import AppLayout from "./AppLayout";
import AcceptInvitationPage from "./pages/AcceptInvitationPage";
import AdminMembers from "./pages/AdminMembers";
import CampaignDetail from "./pages/CampaignDetail";
import CampaignList from "./pages/CampaignList";
import CampaignWizard from "./pages/CampaignWizard";
import AdminAuditLog from "./pages/AdminAuditLog";
import AdminBrowserProfiles from "./pages/AdminBrowserProfiles";
import AdminConnectors from "./pages/AdminConnectors";
import CampaignEvents from "./pages/CampaignEvents";
import EventContentStudioPage from "./pages/EventContentStudioPage";
import EventDetailPage from "./pages/EventDetailPage";
import DashboardOverviewPage from "./pages/DashboardOverviewPage";
import FunnelReportPage from "./pages/FunnelReportPage";
import ContentEffectivenessPage from "./pages/ContentEffectivenessPage";
import SourcePerformancePage from "./pages/SourcePerformancePage";
import BrowserSessionPage from "./pages/BrowserSessionPage";
import EventsInboxPage from "./pages/EventsInboxPage";
import LeadsPipelinePage from "./pages/LeadsPipelinePage";
import NotificationInboxPage from "./pages/NotificationInboxPage";
import NotificationPreferencesPage from "./pages/NotificationPreferencesPage";
import SignInPage from "./pages/SignInPage";
import { AuthProvider, useAuth } from "./components/AuthProvider";

function RequireAuth({ children }: { children: ReactNode }) {
  const { loading, session } = useAuth();
  const location = useLocation();
  useEffect(() => {
    if (loading) return;
    if (!session) {
      // No-op — the redirect below handles the navigation.
    }
  }, [loading, session]);
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-[var(--color-background)] text-xs font-mono text-slate-500"
        data-testid="auth-loading"
      >
        Loading workspace…
      </div>
    );
  }
  if (!session) {
    return <Navigate to="/sign-in" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/sign-in" element={<SignInPage />} />
        <Route
          element={
            <RequireAuth>
              <AppLayout />
            </RequireAuth>
          }
        >
          <Route index element={<DashboardOverviewPage />} />
          <Route path="reports/funnel" element={<FunnelReportPage />} />
          <Route path="reports/source-performance" element={<SourcePerformancePage />} />
          <Route path="reports/content-effectiveness" element={<ContentEffectivenessPage />} />
          <Route path="campaigns" element={<CampaignList />} />
          <Route path="campaigns/new" element={<CampaignWizard />} />
          <Route path="campaigns/:id" element={<CampaignDetail />} />
          <Route path="campaigns/:id/events" element={<CampaignEvents />} />
          <Route path="events/:id" element={<EventDetailPage />} />
          <Route path="events/:id/content" element={<EventContentStudioPage />} />
          <Route path="events" element={<EventsInboxPage />} />
          <Route path="leads" element={<LeadsPipelinePage />} />
          <Route path="browser" element={<BrowserSessionPage />} />
          <Route path="admin" element={<AdminConnectors />} />
          <Route path="admin/connectors" element={<AdminConnectors />} />
          <Route path="admin/browser-profiles" element={<AdminBrowserProfiles />} />
          <Route path="admin/members" element={<AdminMembers />} />
          <Route path="admin/audit-log" element={<AdminAuditLog />} />
          <Route path="notifications" element={<NotificationInboxPage />} />
          <Route path="notification-preferences" element={<NotificationPreferencesPage />} />
        </Route>
        <Route path="/invitations/accept" element={<AcceptInvitationPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
