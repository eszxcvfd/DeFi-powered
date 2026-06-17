// Calendar exports settings page (US-045).

import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import CalendarExportsPanel from "@/components/CalendarExportsPanel";

export default function CalendarExportsPage() {
  return (
    <AppPageShell testId="calendar-exports-page">
      <AppPageHeader
        title="Calendar exports"
        subtitle="Manage the calendar export tokens for the current user. The plaintext is shown only at mint time and cannot be recovered."
      />
      <div className={PAGE_CONTENT_CLASS}>
        <CalendarExportsPanel />
      </div>
    </AppPageShell>
  );
}
