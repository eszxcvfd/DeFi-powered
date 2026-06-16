import { useEffect, useState } from "react";
import { listEventHistory } from "@/api/eventOverrides";
import type { EventChangeHistoryEntry } from "@/types/event";
import { Loader2 } from "lucide-react";

function describeAction(entry: EventChangeHistoryEntry): string {
  if (entry.action === "upserted") {
    return `Override set on ${entry.field}`;
  }
  if (entry.action === "cleared") {
    return `Override cleared on ${entry.field}`;
  }
  if (entry.action === "denied") {
    return `Edit denied on ${entry.field}: ${entry.reason}`;
  }
  if (entry.action === "protected_skipped") {
    return `Merge skipped protected ${entry.field}: ${entry.reason}`;
  }
  return `${entry.action} on ${entry.field}`;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "(empty)";
  if (value instanceof Date) return value.toISOString();
  if (typeof value === "string") return value;
  return String(value);
}

export default function EventHistoryPanel({
  eventId,
  refreshKey = 0,
}: {
  eventId: string;
  refreshKey?: number;
}) {
  const [history, setHistory] = useState<EventChangeHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    listEventHistory(eventId, 50)
      .then((res) => setHistory(res.history))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [eventId, refreshKey]);

  if (loading) {
    return (
      <div className="p-4 flex items-center gap-2 text-xs text-slate-500" data-testid="event-history-loading">
        <Loader2 className="size-3.5 animate-spin" />
        Loading history…
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-xs text-red-600" data-testid="event-history-error">
        {error}
      </p>
    );
  }

  if (history.length === 0) {
    return (
      <p className="text-xs text-slate-500" data-testid="event-history-empty">
        No edit history yet.
      </p>
    );
  }

  return (
    <ul className="space-y-2" data-testid="event-history-list">
      {history.map((entry) => (
        <li
          key={entry.id}
          className="text-xs border border-slate-100 p-2 rounded-md"
          data-testid="event-history-row"
        >
          <div className="flex justify-between gap-2">
            <span className="font-mono text-slate-700">
              {describeAction(entry)}
            </span>
            <span className="text-[10px] text-slate-500">
              {entry.created_at.slice(0, 16).replace("T", " ")}
            </span>
          </div>
          {entry.action === "upserted" ? (
            <p className="text-[11px] text-slate-500 mt-1">
              <span className="font-mono">{formatValue(entry.prior_value)}</span>
              {" → "}
              <span className="font-mono">{formatValue(entry.new_value)}</span>
            </p>
          ) : null}
          {entry.action === "cleared" ? (
            <p className="text-[11px] text-slate-500 mt-1">
              Restored to <span className="font-mono">{formatValue(entry.new_value)}</span>
            </p>
          ) : null}
          <p className="text-[10px] text-slate-400 mt-1">
            actor: {entry.actor_role} {entry.actor_id.slice(0, 8)}
          </p>
          {entry.reason ? (
            <p className="text-[10px] text-slate-500 mt-0.5 italic">
              "{entry.reason}"
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
