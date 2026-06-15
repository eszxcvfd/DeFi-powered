import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Bell, BellRing, Check, X, Settings2, Inbox } from "lucide-react";
import {
  dismissNotification,
  listNotifications,
  markRead,
} from "@/api/notifications";
import { Button } from "@/components/ui/button";
import { runScan } from "@/api/notifications";
import type { NotificationView } from "@/types/notifications";

function formatTs(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
  } catch {
    return iso;
  }
}

function stateBadge(state: string) {
  if (state === "unread") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-amber-50 text-amber-700 border-amber-200">
        <BellRing className="size-3" /> unread
      </span>
    );
  }
  if (state === "dismissed") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-slate-50 text-slate-500 border-slate-200">
        <X className="size-3" /> dismissed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-emerald-50 text-emerald-700 border-emerald-200">
      <Check className="size-3" /> read
    </span>
  );
}

export default function NotificationInboxPage() {
  const [items, setItems] = useState<NotificationView[]>([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [scanResult, setScanResult] = useState<string | null>(null);
  const navigate = useNavigate();

  async function refresh() {
    setItems([]);
    setUnread(0);
    const r = await listNotifications();
    setItems(r.items);
    setUnread(r.unread_count);
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function handleMarkRead(id: string) {
    setBusy(true);
    setError(null);
    try {
      await markRead(id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDismiss(id: string) {
    setBusy(true);
    setError(null);
    try {
      await dismissNotification(id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleScan() {
    setBusy(true);
    setError(null);
    setScanResult(null);
    try {
      const result = await runScan({ include_reminders: true, include_events: true, lead_minutes: 60 });
      setScanResult(
        `Scan complete: ${result.candidates} candidates, ${result.in_app_created} in-app, ${result.emails_attempted} emails sent, ${result.emails_failed} failed.`,
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="min-h-[calc(100vh-4rem)] bg-slate-50/80 px-4 sm:px-6 lg:px-8 py-6"
      data-testid="notification-inbox-page"
    >
      <div className="max-w-[1100px] mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="size-9 bg-slate-900 text-white flex items-center justify-center rounded-sm">
              <Bell className="size-4" />
            </div>
            <div>
              <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">
                LiveLead
              </p>
              <h1 className="text-lg font-bold tracking-tight text-slate-900">
                Notification inbox
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/notification-preferences"
              className="text-xs underline text-slate-600 flex items-center gap-1"
              data-testid="nav-preferences"
            >
              <Settings2 className="size-3" /> Preferences
            </Link>
            <Button
              variant="ghost"
              data-testid="run-scan"
              onClick={() => void handleScan()}
              disabled={busy}
              className="text-xs h-8 border border-slate-200"
            >
              Run scan
            </Button>
          </div>
        </div>

        <p className="text-sm text-slate-600" data-testid="inbox-unread-count">
          {unread} unread of {items.length} total
        </p>

        {scanResult ? (
          <div
            className="border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm px-4 py-3 rounded-sm"
            data-testid="scan-result"
            role="status"
          >
            {scanResult}
          </div>
        ) : null}

        {error ? (
          <div
            className="border border-rose-200 bg-rose-50 text-rose-800 text-sm px-4 py-3 rounded-sm"
            data-testid="inbox-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <div className="bg-white border border-slate-200 rounded-sm" data-testid="inbox-list">
          {items.length === 0 ? (
            <div
              className="px-6 py-12 text-center text-slate-400"
              data-testid="inbox-empty"
            >
              <Inbox className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
              <p className="text-sm">No notifications yet.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {items.map((n) => (
                <li
                  key={n.id}
                  className="px-5 py-4 flex items-start gap-3 hover:bg-slate-50/40"
                  data-testid="notification-row"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p
                        className="text-sm font-semibold text-slate-900 truncate"
                        data-testid="notification-title"
                      >
                        {n.title}
                      </p>
                      {stateBadge(n.state)}
                      <span className="text-[10px] font-mono text-slate-400">
                        {n.notification_type}
                      </span>
                    </div>
                    {n.summary ? (
                      <p className="text-xs text-slate-500 mt-0.5">{n.summary}</p>
                    ) : null}
                    <p className="text-[10px] font-mono text-slate-400 mt-1">
                      {formatTs(n.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    {n.state === "unread" ? (
                      <Button
                        variant="ghost"
                        data-testid="notification-mark-read"
                        className="text-[11px] h-7 border border-slate-200"
                        onClick={() => void handleMarkRead(n.id)}
                        disabled={busy}
                      >
                        <Check className="size-3" /> Read
                      </Button>
                    ) : null}
                    {n.state !== "dismissed" ? (
                      <Button
                        variant="ghost"
                        data-testid="notification-dismiss"
                        className="text-[11px] h-7 border border-slate-200"
                        onClick={() => void handleDismiss(n.id)}
                        disabled={busy}
                      >
                        <X className="size-3" /> Dismiss
                      </Button>
                    ) : null}
                    {n.deep_link ? (
                      <Button
                        variant="ghost"
                        data-testid="notification-open"
                        className="text-[11px] h-7 border border-slate-200"
                        onClick={() => navigate(n.deep_link)}
                      >
                        Open
                      </Button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
