import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  ListChecks,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  acknowledgeAlertEvent,
  createAlertRule,
  deleteAlertRule,
  getOperatorSummary,
  listAlertEvents,
  listAlertRules,
  updateAlertRule,
} from "@/api/observability";
import type {
  AlertEvent,
  AlertRule,
  OperatorSummary,
} from "@/types/observability";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function severityBadge(severity: string) {
  const s = severity.toLowerCase();
  if (s === "critical") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-rose-50 text-rose-700 border-rose-200">
        <AlertTriangle className="size-3" /> critical
      </span>
    );
  }
  if (s === "warning") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-amber-50 text-amber-700 border-amber-200">
        <CircleAlert className="size-3" /> warning
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-slate-50 text-slate-700 border-slate-200">
      {severity}
    </span>
  );
}

function statusBadge(status: string) {
  const s = status.toLowerCase();
  if (s === "firing") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-rose-50 text-rose-700 border-rose-200">
        firing
      </span>
    );
  }
  if (s === "acknowledged") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-amber-50 text-amber-700 border-amber-200">
        acknowledged
      </span>
    );
  }
  if (s === "resolved") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-emerald-50 text-emerald-700 border-emerald-200">
        resolved
      </span>
    );
  }
  if (s === "suppressed") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-slate-50 text-slate-700 border-slate-200">
        suppressed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-slate-50 text-slate-700 border-slate-200">
      {status}
    </span>
  );
}

export function AdminObservabilityPage() {
  const [summary, setSummary] = useState<OperatorSummary | null>(null);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newRule, setNewRule] = useState({
    name: "",
    metric: "backup.age_hours",
    operator: "gt",
    threshold: 0,
    window_seconds: 0,
    severity: "warning",
    cooldown_seconds: 600,
    channels: "in_app",
    enabled: true,
  });

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, r, e] = await Promise.all([
        getOperatorSummary(),
        listAlertRules(),
        listAlertEvents({ limit: 50, offset: 0 }),
      ]);
      setSummary(s);
      setRules(r.items);
      setEvents(e.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const openBySeverity = useMemo(() => summary?.open_alerts_by_severity ?? {}, [summary]);

  const onCreate = async () => {
    try {
      await createAlertRule({
        name: newRule.name,
        metric: newRule.metric,
        operator: newRule.operator,
        threshold: Number(newRule.threshold),
        window_seconds: Number(newRule.window_seconds),
        severity: newRule.severity,
        cooldown_seconds: Number(newRule.cooldown_seconds),
        channels: newRule.channels.split(",").map((c) => c.trim()).filter(Boolean),
        enabled: Boolean(newRule.enabled),
      });
      setNewRule({ ...newRule, name: "" });
      void refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onDelete = async (id: string) => {
    try {
      await deleteAlertRule(id);
      void refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onToggle = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      void refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onAcknowledge = async (event: AlertEvent) => {
    try {
      await acknowledgeAlertEvent(event.id);
      void refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <AppPageShell>
      <AppPageHeader
        title="Observability"
        subtitle="Operator panel for alert rules, recent events, and live readiness."
      />
      <div className={PAGE_CONTENT_CLASS}>
        {error ? (
          <div className="mb-4 p-3 text-sm border border-rose-200 bg-rose-50 text-rose-700 rounded">
            {error}
          </div>
        ) : null}
        {loading ? (
          <div className="text-sm text-slate-500">Loading observability surface…</div>
        ) : null}

        {summary ? (
          <AppSection title="Readiness">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-3 border rounded bg-white">
                <div className="text-[10px] font-mono uppercase text-slate-500">Environment</div>
                <div className="text-sm font-mono mt-1">{summary.environment_mode}</div>
                <div className="mt-1">
                  {summary.gate_passed ? (
                    <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                      <CheckCircle2 className="size-3" /> gate passing
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-xs text-rose-700">
                      <AlertTriangle className="size-3" /> gate blocked
                    </span>
                  )}
                </div>
              </div>
              <div className="p-3 border rounded bg-white">
                <div className="text-[10px] font-mono uppercase text-slate-500">Backup</div>
                <div className="text-sm font-mono mt-1">{summary.backup_freshness}</div>
                <div className="text-xs text-slate-500 mt-1">
                  {summary.backup_age_hours !== null
                    ? `${summary.backup_age_hours.toFixed(2)} h old`
                    : "no backup recorded"}
                </div>
              </div>
              <div className="p-3 border rounded bg-white">
                <div className="text-[10px] font-mono uppercase text-slate-500">Worker heartbeat</div>
                <div className="text-sm font-mono mt-1">
                  {summary.worker_heartbeat_age_seconds !== null
                    ? `${Math.round(summary.worker_heartbeat_age_seconds)} s ago`
                    : "no heartbeat"}
                </div>
              </div>
            </div>
            {summary.gate_blocking.length > 0 ? (
              <div className="mt-3 text-xs">
                <div className="font-mono uppercase text-rose-700">Blocking</div>
                <ul className="list-disc pl-5">
                  {summary.gate_blocking.map((c) => (
                    <li key={c.name}><span className="font-mono">{c.name}</span> — {c.detail}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            {summary.gate_warnings.length > 0 ? (
              <div className="mt-3 text-xs">
                <div className="font-mono uppercase text-amber-700">Warnings</div>
                <ul className="list-disc pl-5">
                  {summary.gate_warnings.map((c) => (
                    <li key={c.name}><span className="font-mono">{c.name}</span> — {c.detail}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <div className="mt-3 text-xs flex flex-wrap gap-3">
              <span>
                Open <span className="font-mono">info</span>: {openBySeverity.info ?? 0}
              </span>
              <span>
                Open <span className="font-mono">warning</span>: {openBySeverity.warning ?? 0}
              </span>
              <span>
                Open <span className="font-mono">critical</span>: {openBySeverity.critical ?? 0}
              </span>
              <span className="ml-auto text-slate-500">
                {summary.rules_enabled}/{summary.rules_total} rules enabled
              </span>
            </div>
          </AppSection>
        ) : null}

        <AppSection title="Rules">
          <div className="overflow-x-auto border rounded bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Metric</th>
                  <th className="px-3 py-2">Threshold</th>
                  <th className="px-3 py-2">Window</th>
                  <th className="px-3 py-2">Severity</th>
                  <th className="px-3 py-2">Channels</th>
                  <th className="px-3 py-2">Enabled</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <tr key={rule.id} className="border-t">
                    <td className="px-3 py-2 font-mono">
                      {rule.name}
                      {rule.is_system ? (
                        <span className="ml-2 text-[10px] text-slate-500">(system)</span>
                      ) : null}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{rule.metric}</td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {rule.operator} {rule.threshold}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      {rule.window_seconds}s
                    </td>
                    <td className="px-3 py-2">{severityBadge(rule.severity)}</td>
                    <td className="px-3 py-2 text-xs">
                      {rule.channels.join(", ")}
                    </td>
                    <td className="px-3 py-2 text-xs">
                      <button
                        onClick={() => void onToggle(rule)}
                        className="underline"
                        disabled={rule.is_system}
                      >
                        {rule.enabled ? "enabled" : "disabled"}
                      </button>
                    </td>
                    <td className="px-3 py-2 text-xs text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void onDelete(rule.id)}
                        disabled={rule.is_system}
                      >
                        <Trash2 className="size-3" /> delete
                      </Button>
                    </td>
                  </tr>
                ))}
                {rules.length === 0 ? (
                  <tr className="border-t">
                    <td colSpan={8} className="px-3 py-2 text-sm text-slate-500">
                      No alert rules configured.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="mt-4 p-3 border rounded bg-slate-50">
            <div className="text-[10px] font-mono uppercase text-slate-500 mb-2">
              Add a user rule
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <div>
                <Label htmlFor="obs-name">Name</Label>
                <Input
                  id="obs-name"
                  value={newRule.name}
                  onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                  placeholder="my.first.rule"
                />
              </div>
              <div>
                <Label htmlFor="obs-metric">Metric</Label>
                <select
                  id="obs-metric"
                  className="w-full px-2 py-1 text-sm border rounded bg-white"
                  value={newRule.metric}
                  onChange={(e) => setNewRule({ ...newRule, metric: e.target.value })}
                >
                  <option value="backup.age_hours">backup.age_hours</option>
                  <option value="worker.heartbeat.age_seconds">worker.heartbeat.age_seconds</option>
                  <option value="connector.failure_rate">connector.failure_rate</option>
                  <option value="discovery.needs_user_action_rate">discovery.needs_user_action_rate</option>
                  <option value="browser.crash_loop">browser.crash_loop</option>
                  <option value="audit.retention_breach_risk">audit.retention_breach_risk</option>
                </select>
              </div>
              <div>
                <Label htmlFor="obs-operator">Operator</Label>
                <select
                  id="obs-operator"
                  className="w-full px-2 py-1 text-sm border rounded bg-white"
                  value={newRule.operator}
                  onChange={(e) => setNewRule({ ...newRule, operator: e.target.value })}
                >
                  <option value="gt">gt</option>
                  <option value="gte">gte</option>
                  <option value="lt">lt</option>
                  <option value="lte">lte</option>
                  <option value="eq">eq</option>
                </select>
              </div>
              <div>
                <Label htmlFor="obs-threshold">Threshold</Label>
                <Input
                  id="obs-threshold"
                  type="number"
                  value={newRule.threshold}
                  onChange={(e) => setNewRule({ ...newRule, threshold: Number(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="obs-window">Window (s)</Label>
                <Input
                  id="obs-window"
                  type="number"
                  value={newRule.window_seconds}
                  onChange={(e) => setNewRule({ ...newRule, window_seconds: Number(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="obs-severity">Severity</Label>
                <select
                  id="obs-severity"
                  className="w-full px-2 py-1 text-sm border rounded bg-white"
                  value={newRule.severity}
                  onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                >
                  <option value="info">info</option>
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                </select>
              </div>
              <div>
                <Label htmlFor="obs-cooldown">Cooldown (s)</Label>
                <Input
                  id="obs-cooldown"
                  type="number"
                  value={newRule.cooldown_seconds}
                  onChange={(e) => setNewRule({ ...newRule, cooldown_seconds: Number(e.target.value) })}
                />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="obs-channels">Channels (comma separated)</Label>
                <Input
                  id="obs-channels"
                  value={newRule.channels}
                  onChange={(e) => setNewRule({ ...newRule, channels: e.target.value })}
                />
              </div>
            </div>
            <div className="mt-3 flex justify-end">
              <Button onClick={() => void onCreate()} disabled={!newRule.name}>
                <ListChecks className="size-3" /> Add rule
              </Button>
            </div>
          </div>
        </AppSection>

        <AppSection title="Recent events">
          <div className="overflow-x-auto border rounded bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500">
                  <th className="px-3 py-2">Fired at</th>
                  <th className="px-3 py-2">Rule</th>
                  <th className="px-3 py-2">Metric</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Severity</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id} className="border-t">
                    <td className="px-3 py-2 font-mono text-xs">
                      {event.fired_at}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{event.rule_name}</td>
                    <td className="px-3 py-2 font-mono text-xs">{event.metric}</td>
                    <td className="px-3 py-2">{statusBadge(event.status)}</td>
                    <td className="px-3 py-2">{severityBadge(event.severity)}</td>
                    <td className="px-3 py-2 text-right text-xs">
                      {event.status === "firing" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => void onAcknowledge(event)}
                        >
                          <ShieldCheck className="size-3" /> acknowledge
                        </Button>
                      ) : null}
                    </td>
                  </tr>
                ))}
                {events.length === 0 ? (
                  <tr className="border-t">
                    <td colSpan={6} className="px-3 py-2 text-sm text-slate-500">
                      <Activity className="size-3 inline mr-1" /> No alert events yet.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </AppSection>
      </div>
    </AppPageShell>
  );
}

export default AdminObservabilityPage;
