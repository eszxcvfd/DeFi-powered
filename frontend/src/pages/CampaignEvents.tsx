import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { listCampaignEvents } from "@/api/events";
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
    <span className={`text-xs font-mono border px-2 py-0.5 rounded-sm ${styles}`} data-testid="event-confidence">
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

  const load = useMemo(
    () => () => {
      if (!id) return Promise.resolve();
      return listCampaignEvents(id, { q: q.trim() || undefined, include_score: false })
        .then(setItems)
        .catch((e) => setError(String(e)))
        .finally(() => setLoading(false));
    },
    [id, q],
  );

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  if (loading) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="size-5 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="campaign-events">
      <Link to={`/campaigns/${id}`} className="text-xs text-[var(--color-muted)] hover:text-slate-900">
        ← Campaign
      </Link>
      <h1 className="text-xl font-bold mt-4 mb-2">Event results</h1>
      <p className="text-sm text-slate-500 mb-4">Review canonical events from discovery with provenance and confidence.</p>
      <input
        type="search"
        placeholder="Filter by title…"
        className="mb-4 w-full max-w-sm border border-slate-200 rounded-sm px-3 py-2 text-sm"
        data-testid="event-list-filter"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No events yet. Run discovery on this campaign first.</p>
      ) : (
        <table className="w-full text-sm border border-slate-200 rounded-sm overflow-hidden">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="p-3">Title</th>
              <th className="p-3">Region</th>
              <th className="p-3">Sources</th>
              <th className="p-3">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {items.map((ev) => (
              <tr key={ev.id} data-testid="event-list-row">
                <td className="p-3">
                  <Link to={`/events/${ev.id}`} className="font-medium text-slate-900 hover:underline">
                    {ev.canonical_title}
                  </Link>
                  {ev.observation_count > 1 && (
                    <span className="ml-2 text-xs text-slate-400">{ev.observation_count} obs</span>
                  )}
                </td>
                <td className="p-3 text-slate-600">{ev.region || "—"}</td>
                <td className="p-3 font-mono text-xs text-slate-600">{ev.source_count}</td>
                <td className="p-3">
                  <ConfidenceBadge summary={ev.confidence_summary} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}