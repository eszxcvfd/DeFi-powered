// Calendar export modal (US-045).
//
// Renders the bounded calendar export surface for
// the current user. The modal explains the
// current-user scope, shows the `text/calendar`
// URL, and offers a `Copy URL` button plus a
// `Mint tokenized feed` button that calls
// `POST /calendar-export-tokens` and shows the
// plaintext token exactly once.


import { useEffect, useState } from "react";
import { Calendar, Clipboard, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  CalendarScope,
  eventIcsUrl,
  mintCalendarExportToken,
  tokenizedIcsUrl,
  watchlistIcsUrl,
} from "@/api/calendarExport";

type Props = {
  open: boolean;
  onClose: () => void;
  scope: CalendarScope;
  eventId?: string | null;
  filterLabel?: string;
};

export default function CalendarExportModal({
  open,
  onClose,
  scope,
  eventId,
  filterLabel,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plaintext, setPlaintext] = useState<string | null>(null);
  const [copied, setCopied] = useState<"url" | "token" | null>(null);

  useEffect(() => {
    if (open) {
      setPlaintext(null);
      setError(null);
      setCopied(null);
    }
  }, [open, scope, eventId, filterLabel]);

  if (!open) return null;

  const directUrl = (() => {
    if (scope === "event" && eventId) return eventIcsUrl(eventId);
    if (scope === "watchlist") return watchlistIcsUrl();
    return null;
  })();

  async function copyToClipboard(value: string, kind: "url" | "token") {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(kind);
    } catch (e) {
      setError(String(e));
    }
  }

  async function mintToken() {
    setBusy(true);
    setError(null);
    try {
      const res = await mintCalendarExportToken({
        scope,
        target_id: scope === "event" ? eventId ?? null : null,
        filter_json:
          scope === "event_filter"
            ? { label: filterLabel ?? "" }
            : null,
      });
      setPlaintext(res.plaintext);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const titleMap: Record<CalendarScope, string> = {
    event: "Export this event to your calendar",
    watchlist: "Subscribe to your watchlist calendar",
    event_filter: "Subscribe to the current event filter",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4"
      data-testid="calendar-export-modal"
    >
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl border border-slate-200">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div className="flex items-center gap-2 text-slate-800">
            <Calendar className="size-4" />
            <h3 className="text-sm font-semibold">{titleMap[scope]}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-500 hover:text-slate-800"
            data-testid="calendar-export-modal-close"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="space-y-4 px-4 py-4 text-sm text-slate-700">
          {scope === "event_filter" && filterLabel ? (
            <p
              className="text-xs font-mono uppercase text-slate-500"
              data-testid="calendar-export-filter-label"
            >
              Filter: {filterLabel}
            </p>
          ) : null}
          {directUrl ? (
            <div className="space-y-2">
              <label className="block text-[11px] font-mono uppercase text-slate-500">
                Direct URL (current-user session)
              </label>
              <div className="flex flex-wrap gap-2 items-center">
                <input
                  className="flex-1 min-w-0 text-xs border border-slate-200 rounded-md px-2 py-1.5 font-mono"
                  data-testid="calendar-export-direct-url"
                  readOnly
                  value={directUrl}
                />
                <Button
                  size="sm"
                  variant="ghost"
                  data-testid="calendar-export-copy-url"
                  disabled={busy}
                  onClick={() => void copyToClipboard(directUrl, "url")}
                  className="gap-1.5"
                >
                  <Clipboard className="size-3.5" />
                  {copied === "url" ? "Copied" : "Copy URL"}
                </Button>
              </div>
            </div>
          ) : null}
          <div className="space-y-2">
            <label className="block text-[11px] font-mono uppercase text-slate-500">
              Tokenized feed (calendar subscription)
            </label>
            <Button
              size="sm"
              data-testid="calendar-export-mint-token"
              disabled={busy}
              onClick={() => void mintToken()}
              className="gap-1.5"
            >
              {busy ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Calendar className="size-3.5" />
              )}
              Mint tokenized feed
            </Button>
            {plaintext ? (
              <div className="space-y-2" data-testid="calendar-export-plaintext">
                <p className="text-xs text-amber-700" data-testid="calendar-export-plaintext-warning">
                  Copy this URL now. The plaintext token is shown only once and
                  cannot be recovered.
                </p>
                <div className="flex flex-wrap gap-2 items-center">
                  <input
                    className="flex-1 min-w-0 text-xs border border-slate-200 rounded-md px-2 py-1.5 font-mono"
                    data-testid="calendar-export-tokenized-url"
                    readOnly
                    value={tokenizedIcsUrl(plaintext)}
                  />
                  <Button
                    size="sm"
                    variant="ghost"
                    data-testid="calendar-export-copy-token"
                    onClick={() =>
                      void copyToClipboard(tokenizedIcsUrl(plaintext), "token")
                    }
                    className="gap-1.5"
                  >
                    <Clipboard className="size-3.5" />
                    {copied === "token" ? "Copied" : "Copy URL"}
                  </Button>
                </div>
              </div>
            ) : null}
          </div>
          {error ? (
            <p className="text-xs text-red-600" data-testid="calendar-export-error">
              {error}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
