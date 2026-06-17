// Calendar exports settings panel (US-045).
//
// Lists the current user's active and revoked
// calendar export tokens, shows the most recent
// export audit entries, and exposes a `Revoke`
// button for each token.

import { useEffect, useState } from "react";
import { Calendar, Loader2, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AppSection } from "@/components/layout/AppSection";
import {
  CalendarExportAudit,
  CalendarExportToken,
  listCalendarExportAudits,
  listCalendarExportTokens,
  revokeCalendarExportToken,
} from "@/api/calendarExport";

function formatDate(value: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleString();
}

function statusForToken(token: CalendarExportToken, now: Date): string {
  if (token.revoked_at) return "Revoked";
  if (token.expires_at && new Date(token.expires_at) <= now) return "Expired";
  return "Active";
}

export default function CalendarExportsPanel() {
  const [tokens, setTokens] = useState<CalendarExportToken[]>([]);
  const [audits, setAudits] = useState<CalendarExportAudit[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [includeRevoked, setIncludeRevoked] = useState(true);

  async function refresh() {
    setBusy(true);
    setError(null);
    try {
      const [tokenList, auditList] = await Promise.all([
        listCalendarExportTokens({ include_revoked: includeRevoked }),
        listCalendarExportAudits({ limit: 20 }),
      ]);
      setTokens(tokenList.items);
      setAudits(auditList.items);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [includeRevoked]);

  async function revoke(id: string) {
    setBusy(true);
    setError(null);
    try {
      await revokeCalendarExportToken(id);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const now = new Date();

  return (
    <div className="space-y-4" data-testid="calendar-exports-panel">
      {error ? (
        <div
          className="border border-rose-200 bg-rose-50 text-rose-800 text-sm px-4 py-3 rounded-sm"
          role="alert"
          data-testid="calendar-exports-error"
        >
          {error}
        </div>
      ) : null}

      <AppSection
        title="Tokens"
        testId="calendar-exports-tokens-section"
        actions={
          <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
            <input
              type="checkbox"
              data-testid="calendar-exports-include-revoked"
              checked={includeRevoked}
              onChange={(e) => setIncludeRevoked(e.target.checked)}
              className="size-3.5"
            />
            Include revoked
          </label>
        }
      >
        {busy && tokens.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loader2 className="size-5 animate-spin text-slate-400" />
          </div>
        ) : tokens.length === 0 ? (
          <p
            className="text-sm text-slate-500 py-4"
            data-testid="calendar-exports-empty"
          >
            No calendar export tokens yet.
          </p>
        ) : (
          <ul className="divide-y divide-slate-100" data-testid="calendar-exports-list">
            {tokens.map((token) => {
              const status = statusForToken(token, now);
              return (
                <li
                  key={token.id}
                  className="py-3 flex flex-wrap items-start gap-4"
                  data-testid="calendar-exports-row"
                >
                  <div className="flex-1 min-w-[200px] space-y-0.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm text-slate-800">
                        {token.scope}
                      </span>
                      <span
                        className={
                          "text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border " +
                          (status === "Active"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : status === "Revoked"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : "bg-slate-50 text-slate-600 border-slate-200")
                        }
                        data-testid="calendar-exports-status"
                      >
                        {status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Target: {token.target_id ?? "—"}
                    </p>
                    <p className="text-xs text-slate-500">
                      Expires: {formatDate(token.expires_at)}
                    </p>
                    <p className="text-xs text-slate-500">
                      Use count: {token.use_count}
                    </p>
                  </div>
                  {status === "Active" ? (
                    <Button
                      size="sm"
                      variant="ghost"
                      data-testid="calendar-exports-revoke"
                      disabled={busy}
                      onClick={() => void revoke(token.id)}
                      className="gap-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                    >
                      {busy ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="size-3.5" />
                      )}
                      Revoke
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </AppSection>

      <AppSection
        title="Recent audit entries"
        testId="calendar-exports-audits-section"
      >
        {audits.length === 0 ? (
          <p
            className="text-sm text-slate-500 py-4"
            data-testid="calendar-exports-audits-empty"
          >
            No audit entries yet.
          </p>
        ) : (
          <ul
            className="divide-y divide-slate-100"
            data-testid="calendar-exports-audits"
          >
            {audits.map((audit) => (
              <li
                key={audit.id}
                className="py-2.5 flex flex-wrap items-center gap-2 text-xs text-slate-600"
                data-testid="calendar-exports-audit-row"
              >
                <span className="text-slate-400 font-mono shrink-0">
                  {formatDate(audit.created_at)}
                </span>
                <span className="text-slate-300">·</span>
                <span className="font-mono">{audit.scope}</span>
                <span className="text-slate-300">·</span>
                <span
                  className={
                    audit.result === "success"
                      ? "text-emerald-700 font-mono"
                      : "text-rose-700 font-mono"
                  }
                >
                  {audit.result}
                </span>
                <span className="text-slate-300">·</span>
                <span className="text-slate-500">
                  {audit.event_count} event{audit.event_count !== 1 ? "s" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </AppSection>

      <div className="flex items-center gap-2 pt-1">
        <Button
          size="sm"
          variant="ghost"
          onClick={() => void refresh()}
          disabled={busy}
          className="gap-1.5 text-slate-600"
          data-testid="calendar-exports-refresh"
        >
          {busy ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Calendar className="size-3.5" />
          )}
          Refresh
        </Button>
      </div>
    </div>
  );
}
