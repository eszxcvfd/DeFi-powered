import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  clearEventOverride,
  patchEvent,
} from "@/api/eventOverrides";
import type { EventFieldProvenance } from "@/types/event";

function formatForInput(field: string, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (field === "starts_at") {
    const d = new Date(value as string);
    if (Number.isNaN(d.getTime())) return "";
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  return String(value);
}

function parseInput(field: string, raw: string): string | null {
  if (!raw) return null;
  if (field === "starts_at") {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  }
  return raw;
}

export default function EventOverridePanel({
  eventId,
  provenance,
  onChanged,
}: {
  eventId: string;
  provenance: EventFieldProvenance[];
  onChanged?: (overrides: EventFieldProvenance[]) => void;
}) {
  const [busyField, setBusyField] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const p of provenance) {
      if (p.is_overridden) {
        next[p.field] = formatForInput(p.field, p.effective_value);
      }
    }
    setDrafts((current) => ({ ...next, ...current }));
  }, [provenance]);

  async function saveField(field: string) {
    setBusyField(field);
    setError(null);
    try {
      const draft = drafts[field] ?? "";
      const parsed = parseInput(field, draft);
      await patchEvent(eventId, {
        updates: { [field]: parsed },
        reason: "Manual override from event detail",
      });
      // Refresh provenance from the server-rendered detail.
      const detail = await fetch(`/events/${eventId}`);
      if (detail.ok) {
        const body = await detail.json();
        onChanged?.(body.overrides ?? []);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyField(null);
    }
  }

  async function clearField(field: string) {
    setBusyField(field);
    setError(null);
    try {
      await clearEventOverride(eventId, field, "Cleared from event detail");
      const detail = await fetch(`/events/${eventId}`);
      if (detail.ok) {
        const body = await detail.json();
        onChanged?.(body.overrides ?? []);
        setDrafts((current) => ({ ...current, [field]: "" }));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyField(null);
    }
  }

  const overrideRows = provenance.filter((p) => p.is_overridden);
  const editable = provenance.filter((p) => !p.is_overridden);

  return (
    <div className="space-y-4" data-testid="event-override-panel">
      <div>
        <h3 className="text-xs font-mono uppercase text-slate-500 mb-2">
          Active overrides
        </h3>
        {overrideRows.length === 0 ? (
          <p
            className="text-xs text-slate-500"
            data-testid="event-override-empty"
          >
            No manual overrides. Edit a field below to lock its value.
          </p>
        ) : (
          <ul className="space-y-2" data-testid="event-override-list">
            {overrideRows.map((row) => (
              <li
                key={row.field}
                className="flex flex-wrap items-center gap-2 text-xs"
                data-testid="event-override-row"
              >
                <span className="font-mono text-slate-600 w-32">{row.field}</span>
                <span
                  className="font-mono text-sky-800"
                  data-testid="event-override-effective"
                >
                  {formatForInput(row.field, row.effective_value)}
                </span>
                <span className="text-slate-400">was</span>
                <span
                  className="font-mono text-slate-500 line-through"
                  data-testid="event-override-source"
                >
                  {formatForInput(row.field, row.source_value)}
                </span>
                <span className="text-[10px] text-slate-500">
                  by {row.actor_role || "system"} @ {row.updated_at?.slice(0, 16) ?? ""}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  data-testid="event-override-clear"
                  disabled={busyField === row.field}
                  onClick={() => void clearField(row.field)}
                >
                  {busyField === row.field ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    "Clear"
                  )}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h3 className="text-xs font-mono uppercase text-slate-500 mb-2">
          Edit a canonical field
        </h3>
        <ul className="space-y-2" data-testid="event-override-editable">
          {editable.map((row) => (
            <li
              key={row.field}
              className="flex flex-wrap items-center gap-2 text-xs"
              data-testid="event-override-editable-row"
            >
              <span className="font-mono text-slate-600 w-32">{row.field}</span>
              <input
                className="border border-slate-200 rounded-md px-2 py-1 text-xs flex-1 min-w-[180px]"
                data-testid="event-override-input"
                value={drafts[row.field] ?? formatForInput(row.field, row.effective_value)}
                onChange={(e) =>
                  setDrafts((current) => ({ ...current, [row.field]: e.target.value }))
                }
                placeholder={formatForInput(row.field, row.source_value)}
              />
              <Button
                size="sm"
                variant="ghost"
                data-testid="event-override-save"
                disabled={busyField === row.field}
                onClick={() => void saveField(row.field)}
              >
                {busyField === row.field ? (
                  <Loader2 className="size-3.5 animate-spin" />
                ) : (
                  "Save override"
                )}
              </Button>
            </li>
          ))}
        </ul>
      </div>
      {error ? (
        <p className="text-xs text-red-600" data-testid="event-override-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
