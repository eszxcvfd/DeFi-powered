import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Bell, Save, Check } from "lucide-react";
import { getPreferences, updatePreferences } from "@/api/notifications";
import { Button } from "@/components/ui/button";
import type { NotificationPreference } from "@/types/notifications";

const TYPE_LABELS: Record<string, string> = {
  job_completed: "Discovery job completed",
  job_needs_user_action: "Discovery job needs action",
  job_failed: "Discovery job failed",
  reminder_due: "Reminder due",
  reminder_overdue: "Reminder overdue",
  event_upcoming: "Event upcoming",
};

export default function NotificationPreferencesPage() {
  const [preferences, setPreferences] = useState<NotificationPreference[]>([]);
  const [draft, setDraft] = useState<Record<string, Record<string, boolean>>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function refresh() {
    const r = await getPreferences();
    setPreferences(r.preferences);
    const next: Record<string, Record<string, boolean>> = {};
    for (const p of r.preferences) {
      next[p.notification_type] = {
        in_app: p.in_app_enabled,
        email: p.email_enabled,
      };
    }
    setDraft(next);
  }

  useEffect(() => {
    void refresh();
  }, []);

  const dirty = useMemo(() => {
    for (const p of preferences) {
      const d = draft[p.notification_type] || {};
      if (d.in_app !== p.in_app_enabled || d.email !== p.email_enabled) return true;
    }
    return false;
  }, [draft, preferences]);

  function setDraftField(type: string, channel: string, value: boolean) {
    setDraft((prev) => ({
      ...prev,
      [type]: { ...(prev[type] || {}), [channel]: value },
    }));
    setSaved(false);
  }

  async function handleSave() {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      const result = await updatePreferences(draft);
      setPreferences(result.preferences);
      setSaved(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="min-h-[calc(100vh-4rem)] bg-slate-50/80 px-4 sm:px-6 lg:px-8 py-6"
      data-testid="notification-preferences-page"
    >
      <div className="max-w-[900px] mx-auto space-y-6">
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
                Notification preferences
              </h1>
            </div>
          </div>
          <Link
            to="/notifications"
            className="text-xs underline text-slate-600"
            data-testid="nav-inbox"
          >
            Back to inbox
          </Link>
        </div>

        <p className="text-sm text-slate-600">
          Choose which notifications you want to receive in-app and via email.
          Email delivery is bounded to high-value signals; the in-app channel
          covers every notification type.
        </p>

        {error ? (
          <div
            className="border border-rose-200 bg-rose-50 text-rose-800 text-sm px-4 py-3 rounded-sm"
            data-testid="preferences-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}

        <div
          className="bg-white border border-slate-200 rounded-sm divide-y divide-slate-100"
          data-testid="preferences-table"
        >
          {preferences.map((p) => {
            const d = draft[p.notification_type] || { in_app: p.in_app_enabled, email: p.email_enabled };
            return (
              <div
                key={p.notification_type}
                className="px-5 py-3 flex items-center gap-4"
                data-testid="preference-row"
              >
                <div className="flex-1">
                  <p className="text-sm font-semibold text-slate-900">
                    {TYPE_LABELS[p.notification_type] || p.notification_type}
                  </p>
                  <p className="text-[10px] font-mono text-slate-400">
                    {p.notification_type}
                  </p>
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    data-testid={`pref-in-app-${p.notification_type}`}
                    checked={!!d.in_app}
                    onChange={(e) => setDraftField(p.notification_type, "in_app", e.target.checked)}
                    className="size-4"
                  />
                  In-app
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-600">
                  <input
                    type="checkbox"
                    data-testid={`pref-email-${p.notification_type}`}
                    checked={!!d.email}
                    onChange={(e) => setDraftField(p.notification_type, "email", e.target.checked)}
                    className="size-4"
                  />
                  Email
                </label>
              </div>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          <Button
            type="button"
            data-testid="preferences-save"
            onClick={() => void handleSave()}
            disabled={busy || !dirty}
            className="rounded-sm text-sm font-semibold h-9 flex items-center gap-1.5"
          >
            <Save className="size-4" /> Save preferences
          </Button>
          {saved ? (
            <span
              className="text-xs text-emerald-700 font-mono flex items-center gap-1"
              data-testid="preferences-saved"
            >
              <Check className="size-3" /> Saved
            </span>
          ) : null}
          {dirty && !saved ? (
            <span
              className="text-xs text-amber-700 font-mono"
              data-testid="preferences-dirty"
            >
              unsaved changes
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
