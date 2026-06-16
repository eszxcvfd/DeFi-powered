import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listCampaignEvents } from "@/api/events";
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
    <span className={`text-xs font-mono border px-2 py-0.5 rounded-full ${styles}`} data-testid="event-confidence">
      {summary}
    </span>
  );
}

export default function CampaignEvents() {
  const { id } = useParams<{ id: string }>();
  const [items, setItems] = useState<CampaignEventListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [watched, setWatched] = useState<"all" | "watched" | "unwatched">("all");

  const load = useMemo(
    () => () => {
      if (!id) return Promise.resolve();
      const watchedParam = watched === "all" ? undefined : watched === "watched";
      return listCampaignEvents(id, {
        q: q.trim() || undefined,
        include_score: false,
        watched: watchedParam,
      })
        .then(setItems)
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false));
    },
    [id, q, watched],
  );

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  useEffect(() => {
    setPage(1);
  }, [q, watched]);

  const pageItems = paginateSlice(items, page);

  if (loading) {
    return (
      <AppPageShell>
        <div className="p-10 flex justify-center">
          <Loader2 className="size-5 animate-spin text-slate-400" />
        </div>
      </AppPageShell>
    );
  }

  return (
    <AppPageShell testId="campaign-events">
      <AppPageHeader
        backTo={`/campaigns/${id}`}
        backLabel="Campaign"
        title="Event results"
        subtitle="Up to 10 events per page. Use filter then Next for more."
      />
      <div className={PAGE_CONTENT_CLASS}>
        <AppSection
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
        >
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <input
              type="search"
              placeholder="Filter by title…"
              className="border border-slate-200 rounded-md px-3 py-2 text-sm w-full max-w-md"
              data-testid="event-list-filter"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <select
              className="text-xs border border-slate-200 rounded-md px-2 py-1.5 bg-white"
              data-testid="event-list-watched-filter"
              value={watched}
              onChange={(e) => setWatched(e.target.value as "all" | "watched" | "unwatched")}
            >
              <option value="all">All</option>
              <option value="watched">Watched</option>
              <option value="unwatched">Unwatched</option>
            </select>
          </div>
          {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
          {items.length === 0 ? (
            <p className="text-sm text-slate-500">No events yet. Run discovery on this campaign first.</p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-md border border-slate-100">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="p-3">Title</th>
                      <th className="p-3">Region</th>
                      <th className="p-3">Sources</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Watched</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {pageItems.map((ev) => (
                      <tr key={ev.id} data-testid="event-list-row">
                        <td className="p-3">
                          <Link to={`/events/${ev.id}`} className="font-medium text-slate-900 hover:underline">
                            {ev.canonical_title}
                          </Link>
                        </td>
                        <td className="p-3 text-slate-600">{ev.region || "—"}</td>
                        <td className="p-3 text-slate-600 font-mono text-xs">{ev.source_count ?? "—"}</td>
                        <td className="p-3">
                          <ConfidenceBadge summary={ev.confidence_summary} />
                        </td>
                        <td className="p-3">
                          {ev.watch?.is_watched ? (
                            <span
                              className="text-xs font-mono border px-2 py-0.5 rounded-full text-sky-800 bg-sky-50 border-sky-200"
                              data-testid="event-list-watched"
                            >
                              {ev.watch.reminder_status === "overdue"
                                ? "Overdue"
                                : ev.watch.reminder_at
                                  ? "Reminder"
                                  : "Watching"}
                            </span>
                          ) : (
                            <span
                              className="text-xs text-slate-400"
                              data-testid="event-list-not-watched"
                            >
                              —
                            </span>
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
                testId="campaign-events-pagination"
              />
            </>
          )}
        </AppSection>
      </div>
    </AppPageShell>
  );
}