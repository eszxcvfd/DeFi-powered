import { Route, Routes } from "react-router-dom";
import AppLayout from "./AppLayout";
import CampaignDetail from "./pages/CampaignDetail";
import CampaignList from "./pages/CampaignList";
import CampaignWizard from "./pages/CampaignWizard";
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

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
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
      </Route>
    </Routes>
  );
}