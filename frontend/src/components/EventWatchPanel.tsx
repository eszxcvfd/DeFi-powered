import { useEffect, useState } from "react";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  removeEventWatchlist,
  upsertEventWatchlist,
} from "@/api/eventWatchlist";
import type { EventWatchState } from "@/types/event";

function toLocalInputValue(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  // datetime-local expects "YYYY-MM-DDTHH:mm" without timezone.
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

export default function EventWatchPanel({
  eventId,
  watch,
  onChanged,
}: {
  eventId: string;
  watch: EventWatchState;
  onChanged?: (state: EventWatchState) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reminderInput, setReminderInput] = useState<string>(
    toLocalInputValue(watch.reminder_at),
  );
  const [reminderNote, setReminderNote] = useState<string>(watch.reminder_note);

  useEffect(() => {
    setReminderInput(toLocalInputValue(watch.reminder_at));
    setReminderNote(watch.reminder_note);
  }, [watch.reminder_at, watch.reminder_note]);

  async function applyWatch(reminderIso: string | null, note: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await upsertEventWatchlist(eventId, {
        reminder_at: reminderIso,
        reminder_note: note,
      });
      onChanged?.(res.watch);
      setReminderInput(toLocalInputValue(res.watch.reminder_at));
      setReminderNote(res.watch.reminder_note);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function unwatch() {
    setBusy(true);
    setError(null);
    try {
      const res = await removeEventWatchlist(eventId);
      onChanged?.(res.watch);
      setReminderInput("");
      setReminderNote("");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3" data-testid="event-watch-panel">
      <div className="flex flex-wrap items-center gap-2">
        {watch.is_watched ? (
          <>
            <span
              className="text-xs font-mono border px-2 py-0.5 rounded-full text-sky-800 bg-sky-50 border-sky-200"
              data-testid="event-watch-state"
            >
              {watch.reminder_status === "overdue"
                ? "Watching · reminder overdue"
                : watch.reminder_status === "scheduled" && watch.reminder_at
                  ? "Watching · reminder set"
                  : "Watching"}
            </span>
            <Button
              size="sm"
              variant="ghost"
              data-testid="event-unwatch"
              disabled={busy}
              onClick={() => void unwatch()}
              className="gap-1.5"
            >
              {busy ? <Loader2 className="size-3.5 animate-spin" /> : <EyeOff className="size-3.5" />}
              Unwatch
            </Button>
          </>
        ) : (
          <Button
            size="sm"
            data-testid="event-watch"
            disabled={busy}
            onClick={() => void applyWatch(null, "")}
            className="gap-1.5"
          >
            {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Eye className="size-3.5" />}
            Watch event
          </Button>
        )}
      </div>
      {watch.is_watched ? (
        <div className="space-y-2" data-testid="event-watch-reminder">
          <label className="block text-[11px] font-mono uppercase text-slate-500">
            Reminder (optional)
          </label>
          <div className="flex flex-wrap gap-2 items-center">
            <input
              type="datetime-local"
              className="text-xs border border-slate-200 rounded-md px-2 py-1.5"
              data-testid="event-watch-reminder-input"
              value={reminderInput}
              onChange={(e) => setReminderInput(e.target.value)}
            />
            <Button
              size="sm"
              variant="ghost"
              data-testid="event-watch-reminder-save"
              disabled={busy}
              onClick={() =>
                void applyWatch(fromLocalInputValue(reminderInput), reminderNote)
              }
            >
              Save reminder
            </Button>
            {watch.reminder_at ? (
              <Button
                size="sm"
                variant="ghost"
                data-testid="event-watch-reminder-clear"
                disabled={busy}
                onClick={() => {
                  setReminderInput("");
                  void applyWatch(null, reminderNote);
                }}
              >
                Clear
              </Button>
            ) : null}
          </div>
          <label className="block text-[11px] font-mono uppercase text-slate-500">
            Note (optional)
          </label>
          <textarea
            className="w-full text-xs border border-slate-200 rounded-md px-2 py-1.5"
            data-testid="event-watch-note"
            value={reminderNote}
            onChange={(e) => setReminderNote(e.target.value)}
            maxLength={500}
            rows={2}
            placeholder="Why is this event worth revisiting?"
          />
        </div>
      ) : null}
      {error ? (
        <p className="text-xs text-red-600" data-testid="event-watch-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
