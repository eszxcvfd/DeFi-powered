import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listOrganizationEvents } from "@/api/events";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import type { CampaignEventListItem } from "@/types/event";
import { Loader2 } from "lucide-react";

function ConfidenceBadge({ summary }: { summary: string }) {
  const styles =
    summary === "high"
      ? "text-emerald-800 bg-emerald-50 border-emerald-200"
      : summary === "merged"
        ? "text-violet-800 bg-violet-50 border-violet-200"
        : "text-amber-800 bg-amber-50 border-amber-200";
  return (
    <span className={`text-xs font-mono border px-2 py-0.5 rounded-full ${styles}`}>{summary}</span>
  );
}

export default function EventsInboxPage() {
  const [items, setItems] = useState<CampaignEventListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await listOrganizationEvents({ q: q.trim() || undefined, limit: 500 }));
    } catch (e) {
      setItems([]);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [q]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [q]);

  const pageItems = paginateSlice(items, page);

  return (
    <AppPageShell testId="events-inbox">
      <AppPageHeader
        title="Events"
        actions={
          <Link
            to="/events/watched"
            className="text-xs font-medium text-slate-700 underline"
            data-testid="open-watched-events"
          >
            Watched events
          </Link>
        }
        subtitle={
          <>
            Canonical events across campaigns. Per-campaign lists under{" "}
            <Link to="/campaigns" className="underline font-medium text-slate-700">
              Campaigns
            </Link>
            .
          </>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        <AppSection
          title="Inbox"
          description="Up to 10 events per page. Open a row for scoring, audience, engagement, content, and browser session."
        >
          <input
            type="search"
            placeholder="Filter by title…"
            className="mb-4 w-full max-w-md border border-slate-200 rounded-md px-3 py-2 text-sm bg-white"
            data-testid="events-inbox-filter"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {error && (
            <p className="text-sm text-red-600 mb-4" data-testid="events-inbox-error">
              {error}
            </p>
          )}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="size-4 animate-spin" />
              Loading events…
            </div>
          )}
          {!loading && items.length === 0 && (
            <p className="text-sm text-slate-500" data-testid="events-inbox-empty">
              No events yet. Run discovery on a campaign to populate this inbox.
            </p>
          )}
          {!loading && items.length > 0 && (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-100">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="p-3">Title</th>
                      <th className="p-3">Campaign</th>
                      <th className="p-3">Region</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Watched</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {pageItems.map((ev) => (
                      <tr key={ev.id} data-testid="events-inbox-row" className="hover:bg-slate-50/80">
                        <td className="p-3">
                          <Link to={`/events/${ev.id}`} className="font-medium text-slate-900 hover:underline">
                            {ev.canonical_title}
                          </Link>
                        </td>
                        <td className="p-3">
                          <Link
                            to={`/campaigns/${ev.campaign_id}/events`}
                            className="text-slate-600 hover:underline text-xs"
                          >
                            {ev.campaign_name || ev.campaign_id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="p-3 text-slate-600">{ev.region || "—"}</td>
                        <td className="p-3">
                          <ConfidenceBadge summary={ev.confidence_summary} />
                        </td>
                        <td className="p-3">
                          {ev.watch?.is_watched ? (
                            <span
                              className="text-xs font-mono border px-2 py-0.5 rounded-full text-sky-800 bg-sky-50 border-sky-200"
                              data-testid="events-inbox-watched"
                            >
                              {ev.watch.reminder_status === "overdue"
                                ? "Overdue"
                                : ev.watch.reminder_at
                                  ? "Reminder"
                                  : "Watching"}
                            </span>
                          ) : (
                            <span className="text-xs text-slate-400" data-testid="events-inbox-not-watched">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ListPagination
                page={page}
                totalItems={items.length}
                onPageChange={setPage}
                testId="events-inbox-pagination"
              />
            </>
          )}
        </AppSection>
      </div>
    </AppPageShell>
  );
}