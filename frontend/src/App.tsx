import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./AppLayout";
import CampaignDetail from "./pages/CampaignDetail";
import CampaignList from "./pages/CampaignList";
import CampaignWizard from "./pages/CampaignWizard";
import AdminConnectors from "./pages/AdminConnectors";
import CampaignEvents from "./pages/CampaignEvents";
import EventContentStudioPage from "./pages/EventContentStudioPage";
import EventDetailPage from "./pages/EventDetailPage";
import LeadsPipelinePage from "./pages/LeadsPipelinePage";

function Placeholder({ title }: { title: string }) {
  return (
    <div className="p-10">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="text-[var(--color-muted)] mt-2">Planned in later stories.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/campaigns" replace />} />
        <Route path="campaigns" element={<CampaignList />} />
        <Route path="campaigns/new" element={<CampaignWizard />} />
        <Route path="campaigns/:id" element={<CampaignDetail />} />
        <Route path="campaigns/:id/events" element={<CampaignEvents />} />
        <Route path="events/:id" element={<EventDetailPage />} />
        <Route path="events/:id/content" element={<EventContentStudioPage />} />
        <Route path="events" element={<Placeholder title="Events" />} />
        <Route path="leads" element={<LeadsPipelinePage />} />
        <Route path="browser" element={<Placeholder title="Browser session" />} />
        <Route path="admin" element={<AdminConnectors />} />
        <Route path="admin/connectors" element={<AdminConnectors />} />
      </Route>
    </Routes>
  );
}