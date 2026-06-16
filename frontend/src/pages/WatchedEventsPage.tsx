import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listWatchedEvents, type WatchedEventRow } from "@/api/eventWatchlist";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

type Filter = "all" | "with-reminder" | "without-reminder";

function ReminderBadge({ row }: { row: WatchedEventRow }) {
  if (row.reminder_status === "overdue") {
    return (
      <span
        className="text-xs font-mono border px-2 py-0.5 rounded-full text-rose-800 bg-rose-50 border-rose-200"
        data-testid="watchlist-reminder-overdue"
      >
        overdue {row.reminder_at?.slice(0, 10) ?? ""}
      </span>
    );
  }
  if (row.reminder_at) {
    return (
      <span
        className="text-xs font-mono border px-2 py-0.5 rounded-full text-sky-800 bg-sky-50 border-sky-200"
        data-testid="watchlist-reminder-scheduled"
      >
        reminder {row.reminder_at.slice(0, 10)}
      </span>
    );
  }
  return (
    <span
      className="text-xs font-mono border px-2 py-0.5 rounded-full text-slate-600 bg-slate-50 border-slate-200"
      data-testid="watchlist-watching"
    >
      watching
    </span>
  );
}

export default function WatchedEventsPage() {
  const [rows, setRows] = useState<WatchedEventRow[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    const hasReminder = filter === "with-reminder" ? true : filter === "without-reminder" ? false : undefined;
    listWatchedEvents(hasReminder)
      .then((res) => setRows(res.items))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <AppPageShell testId="watched-events-page">
      <AppPageHeader
        backTo="/events"
        backLabel="Events"
        title="Watched events"
        subtitle="Your saved events. Reopen them quickly and update reminders from here."
      />
      <div className={PAGE_CONTENT_CLASS}>
        <AppSection
          title="Filter"
          testId="watched-events-filter"
          actions={
            <div className="flex gap-2">
              <Button
                size="sm"
                variant={filter === "all" ? "default" : "ghost"}
                data-testid="watchlist-filter-all"
                onClick={() => setFilter("all")}
              >
                All
              </Button>
              <Button
                size="sm"
                variant={filter === "with-reminder" ? "default" : "ghost"}
                data-testid="watchlist-filter-with-reminder"
                onClick={() => setFilter("with-reminder")}
              >
                With reminder
              </Button>
              <Button
                size="sm"
                variant={filter === "without-reminder" ? "default" : "ghost"}
                data-testid="watchlist-filter-without-reminder"
                onClick={() => setFilter("without-reminder")}
              >
                Watching only
              </Button>
            </div>
          }
        >
          {loading ? (
            <div className="p-6 flex justify-center">
              <Loader2 className="size-5 animate-spin text-slate-400" />
            </div>
          ) : error ? (
            <p className="text-sm text-red-600" data-testid="watched-events-error">
              {error}
            </p>
          ) : rows.length === 0 ? (
            <p
              className="text-sm text-slate-500"
              data-testid="watched-events-empty"
            >
              No events are being tracked yet. Open an event from discovery and use the watch toggle to start tracking it.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100" data-testid="watched-events-list">
              {rows.map((row) => (
                <li
                  key={row.entry_id}
                  className="py-3 flex flex-wrap items-start gap-4"
                  data-testid="watched-event-row"
                >
                  <div className="flex-1 min-w-[200px]">
                    <Link
                      to={`/events/${row.event_id}`}
                      className="font-medium text-slate-900 hover:underline"
                      data-testid="watched-event-link"
                    >
                      {row.canonical_title}
                    </Link>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {row.campaign_name} · {row.region || "—"} · {row.observed_at.slice(0, 10)}
                    </p>
                    {row.reminder_note ? (
                      <p className="text-xs text-slate-500 mt-1 italic">"{row.reminder_note}"</p>
                    ) : null}
                  </div>
                  <ReminderBadge row={row} />
                </li>
              ))}
            </ul>
          )}
        </AppSection>
      </div>
    </AppPageShell>
  );
}
