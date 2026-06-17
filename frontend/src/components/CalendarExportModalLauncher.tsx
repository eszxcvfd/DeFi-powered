// Calendar export modal launcher (US-045).
//
// A small wrapper that renders a single button which
// opens the bounded calendar export modal. The wrapper
// is used on the event detail surface and the
// watched-events list so each entry point can pre-fill
// the right scope and target.

import { useState } from "react";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import CalendarExportModal from "@/components/CalendarExportModal";
import type { CalendarScope } from "@/api/calendarExport";

type Props = {
  eventId?: string | null;
  scope: CalendarScope;
  label?: string;
  filterLabel?: string;
  testId?: string;
};

export default function CalendarExportModalLauncher({
  eventId,
  scope,
  label,
  filterLabel,
  testId,
}: Props) {
  const [open, setOpen] = useState(false);
  const buttonLabel = label ?? "Export to calendar";
  return (
    <>
      <Button
        size="sm"
        variant="ghost"
        data-testid={testId ?? "calendar-export-open"}
        onClick={() => setOpen(true)}
        className="gap-1.5"
      >
        <Calendar className="size-3.5" />
        {buttonLabel}
      </Button>
      <CalendarExportModal
        open={open}
        onClose={() => setOpen(false)}
        scope={scope}
        eventId={eventId ?? null}
        filterLabel={filterLabel}
      />
    </>
  );
}
