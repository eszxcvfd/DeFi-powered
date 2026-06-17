import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  CircleAlert,
  ListChecks,
  ShieldCheck,
  Trash2,
  Shield,
  Database,
  LineChart,
  Globe,
  Zap,
  Play,
  RefreshCw,
  AlertCircle,
  Eye,
  History,
  Settings2,
} from "lucide-react";
import {
  acknowledgeAlertEvent,
  createAlertRule,
  deleteAlertRule,
  getOperatorSummary,
  listAlertEvents,
  listAlertRules,
  updateAlertRule,
  enterPilotLive,
  pauseEnvironment,
  rollbackEnvironment,
  listCutoverEvents,
  getExportPolicy,
  updateExportPolicy,
  testExportPolicy,
  getRetentionPolicy,
  updateRetentionPolicy,
  pruneExpiredBackups,
  dryRunRestore,
  rehearsalRestore,
  deleteData,
  getPerformanceSummary,
  runPerformanceScenario,
  getConnectorHealthSummary,
  computeConnectorHealthSnapshot,
  getConnectorHealthErrors,
  listBackupSnapshots,
  verifyBackupSnapshot,
  restoreBackupSnapshot,
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
import { OrganizationLocalePanel } from "@/components/OrganizationLocalePanel";
import { useAuth } from "@/components/AuthProvider";

type TabId = "alerting" | "cutover" | "health" | "metrics" | "backups" | "performance" | "locale";

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
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-rose-50 text-rose-700 border-rose-200 animate-pulse">
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
  const { session } = useAuth();
  const [activeTab, setActiveTab] = useState<TabId>("alerting");
  const [summary, setSummary] = useState<OperatorSummary | null>(null);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
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

  // US-040 Cutover Form states
  const [cutoverReason, setCutoverReason] = useState("");
  const [cutoverNotes, setCutoverNotes] = useState("");
  const [cutoverPin, setCutoverPin] = useState("");
  const [cutoverRollbackMode, setCutoverRollbackMode] = useState("test_like");
  const [cutoverEvents, setCutoverEvents] = useState<any[]>([]);
  const [cutoverActionBusy, setCutoverActionBusy] = useState(false);

  // US-046 Connector Health states
  const [connectorHealth, setConnectorHealth] = useState<any[]>([]);
  const [healthErrorLogs, setHealthErrorLogs] = useState<{ source_id: string; errors: any[] } | null>(null);
  const [connectorActionBusy, setConnectorActionBusy] = useState(false);

  // US-042 Metrics Export Policy states
  const [metricsPolicy, setMetricsPolicy] = useState({
    prometheus_cidr_blocks: "",
    prometheus_scrape_token: "",
    sentry_dsn: "",
    sentry_environment: "",
  });
  const [metricsSuccessMsg, setMetricsSuccessMsg] = useState<string | null>(null);
  const [metricsActionBusy, setMetricsActionBusy] = useState(false);

  // US-043 Backups & Deletion states
  const [backups, setBackups] = useState<any[]>([]);
  const [retentionPolicy, setRetentionPolicy] = useState({
    backup_retention_days: 30,
    audit_retention_days: 90,
    prune_enabled: true,
  });
  const [restoreDryRunResult, setRestoreDryRunResult] = useState<any | null>(null);
  const [restoreResult, setRestoreResult] = useState<any | null>(null);
  const [gdprTarget, setGdprTarget] = useState("lead");
  const [gdprTargetId, setGdprTargetId] = useState("");
  const [gdprAcceptedBy, setGdprAcceptedBy] = useState("");
  const [gdprReason, setGdprReason] = useState("");
  const [gdprSuccessMsg, setGdprSuccessMsg] = useState<string | null>(null);
  const [backupsBusy, setBackupsBusy] = useState(false);

  // US-044 Performance diagnostics states
  const [perfSummary, setPerfSummary] = useState<any[]>([]);
  const [perfScenarioToRun, setPerfScenarioToRun] = useState("api_read_latency");
  const [perfRunResult, setPerfRunResult] = useState<any | null>(null);
  const [perfActionBusy, setPerfActionBusy] = useState(false);

  const refreshAlerts = async () => {
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
    }
  };

  const loadTabData = async (tab: TabId) => {
    setError(null);
    setLoading(true);
    try {
      if (tab === "alerting") {
        await refreshAlerts();
      } else if (tab === "cutover") {
        const [s, res] = await Promise.all([getOperatorSummary(), listCutoverEvents()]);
        setSummary(s);
        setCutoverEvents(res.events || []);
      } else if (tab === "health") {
        const res = await getConnectorHealthSummary();
        setConnectorHealth(res.entries || []);
      } else if (tab === "metrics") {
        const policy = await getExportPolicy();
        setMetricsPolicy({
          prometheus_cidr_blocks: policy.prometheus_cidr_blocks?.join(", ") || "",
          prometheus_scrape_token: policy.prometheus_scrape_token || "",
          sentry_dsn: policy.sentry_dsn || "",
          sentry_environment: policy.sentry_environment || "",
        });
      } else if (tab === "backups") {
        const [snapRes, ret] = await Promise.all([
          listBackupSnapshots(),
          getRetentionPolicy(),
        ]);
        setBackups(snapRes.snapshots || []);
        setRetentionPolicy({
          backup_retention_days: ret.backup_retention_days || 30,
          audit_retention_days: ret.audit_retention_days || 90,
          prune_enabled: ret.prune_enabled ?? true,
        });
      } else if (tab === "performance") {
        const res = await getPerformanceSummary();
        setPerfSummary(res.entries || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTabData(activeTab);
  }, [activeTab]);

  const openBySeverity = useMemo(() => summary?.open_alerts_by_severity ?? {}, [summary]);

  // Alert Rule handlers
  const onCreateRule = async () => {
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
      void refreshAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onDeleteRule = async (id: string) => {
    try {
      await deleteAlertRule(id);
      void refreshAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onToggleRule = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.id, { enabled: !rule.enabled });
      void refreshAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const onAcknowledgeEvent = async (event: AlertEvent) => {
    try {
      await acknowledgeAlertEvent(event.id);
      void refreshAlerts();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  // Cutover handlers
  const handleEnterPilotLive = async () => {
    if (!cutoverReason.trim()) return setError("Reason is required to execute pilot live cutover");
    setCutoverActionBusy(true);
    setError(null);
    try {
      await enterPilotLive({
        reason: cutoverReason,
        notes: cutoverNotes || undefined,
        admin_pin: cutoverPin || undefined,
      });
      setCutoverReason("");
      setCutoverNotes("");
      setCutoverPin("");
      await loadTabData("cutover");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCutoverActionBusy(false);
    }
  };

  const handlePauseEnv = async () => {
    if (!cutoverReason.trim()) return setError("Reason is required to pause the environment");
    setCutoverActionBusy(true);
    setError(null);
    try {
      await pauseEnvironment({
        reason: cutoverReason,
        notes: cutoverNotes || undefined,
      });
      setCutoverReason("");
      setCutoverNotes("");
      await loadTabData("cutover");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCutoverActionBusy(false);
    }
  };

  const handleRollbackEnv = async () => {
    if (!cutoverReason.trim()) return setError("Reason is required to rollback the environment");
    setCutoverActionBusy(true);
    setError(null);
    try {
      await rollbackEnvironment({
        reason: cutoverReason,
        notes: cutoverNotes || undefined,
        target_mode: cutoverRollbackMode,
      });
      setCutoverReason("");
      setCutoverNotes("");
      await loadTabData("cutover");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setCutoverActionBusy(false);
    }
  };

  // Connector Health handlers
  const handleComputeHealthSnapshot = async (sourceId: string) => {
    setConnectorActionBusy(true);
    setError(null);
    try {
      await computeConnectorHealthSnapshot(sourceId);
      await loadTabData("health");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnectorActionBusy(false);
    }
  };

  const handleViewHealthErrors = async (sourceId: string) => {
    setConnectorActionBusy(true);
    setError(null);
    try {
      const res = await getConnectorHealthErrors(sourceId);
      setHealthErrorLogs({ source_id: sourceId, errors: res.errors || [] });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnectorActionBusy(false);
    }
  };

  // Metrics policy handlers
  const handleSaveMetricsPolicy = async () => {
    setMetricsActionBusy(true);
    setError(null);
    setMetricsSuccessMsg(null);
    try {
      await updateExportPolicy({
        prometheus_cidr_blocks: metricsPolicy.prometheus_cidr_blocks.split(",").map(c => c.trim()).filter(Boolean),
        prometheus_scrape_token: metricsPolicy.prometheus_scrape_token || undefined,
        sentry_dsn: metricsPolicy.sentry_dsn || undefined,
        sentry_environment: metricsPolicy.sentry_environment || undefined,
      });
      setMetricsSuccessMsg("Metrics export policy saved successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setMetricsActionBusy(false);
    }
  };

  const handleTestMetricsConnection = async () => {
    setMetricsActionBusy(true);
    setError(null);
    setMetricsSuccessMsg(null);
    try {
      const res = await testExportPolicy();
      if (res.success) {
        setMetricsSuccessMsg("Metrics export connection test succeeded!");
      } else {
        setError(`Metrics export connection test failed: ${res.detail || "Unknown error"}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setMetricsActionBusy(false);
    }
  };

  // Backups and Retention handlers
  const handleSaveRetentionPolicy = async () => {
    setBackupsBusy(true);
    setError(null);
    try {
      await updateRetentionPolicy({
        backup_retention_days: Number(retentionPolicy.backup_retention_days),
        audit_retention_days: Number(retentionPolicy.audit_retention_days),
        prune_enabled: Boolean(retentionPolicy.prune_enabled),
        accepted_by: session?.email || "owner",
      });
      await loadTabData("backups");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handlePruneBackups = async () => {
    setBackupsBusy(true);
    setError(null);
    try {
      const res = await pruneExpiredBackups();
      alert(`Pruned backups successfully. Deleted count: ${res.deleted_count}`);
      await loadTabData("backups");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handleDryRunRestore = async (backupId: string) => {
    setBackupsBusy(true);
    setError(null);
    setRestoreDryRunResult(null);
    try {
      const res = await dryRunRestore(backupId);
      setRestoreDryRunResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handleRehearsalRestore = async (backupId: string) => {
    setBackupsBusy(true);
    setError(null);
    try {
      const res = await rehearsalRestore(backupId);
      alert(`Rehearsal scheduled. Run status: ${res.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handleVerifyBackup = async (backupId: string, status: string) => {
    setBackupsBusy(true);
    setError(null);
    try {
      await verifyBackupSnapshot(backupId, status);
      await loadTabData("backups");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handleRealRestore = async (backupId: string) => {
    const acceptedBy = prompt("Executing a REAL restore. This will overwrite current data. Type your email/name to accept:");
    if (!acceptedBy) return;
    setBackupsBusy(true);
    setError(null);
    setRestoreResult(null);
    try {
      const res = await restoreBackupSnapshot(backupId, acceptedBy);
      setRestoreResult(res);
      alert("Database restore completed successfully!");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  const handleGdprDeletion = async () => {
    if (!gdprTargetId.trim() || !gdprAcceptedBy.trim() || !gdprReason.trim()) {
      return setError("All data deletion fields are required.");
    }
    setBackupsBusy(true);
    setError(null);
    setGdprSuccessMsg(null);
    try {
      const res = await deleteData({
        target: gdprTarget,
        target_id: gdprTargetId,
        accepted_by: gdprAcceptedBy,
        reason: gdprReason,
      });
      setGdprSuccessMsg(`GDPR deletion request accepted. Target ${res.target} status: ${res.status}`);
      setGdprTargetId("");
      setGdprAcceptedBy("");
      setGdprReason("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBackupsBusy(false);
    }
  };

  // Performance diagnostics handlers
  const handleRunPerfScenario = async () => {
    setPerfActionBusy(true);
    setError(null);
    setPerfRunResult(null);
    try {
      const res = await runPerformanceScenario(perfScenarioToRun);
      setPerfRunResult(res);
      await loadTabData("performance");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPerfActionBusy(false);
    }
  };

  return (
    <AppPageShell testId="admin-observability">
      <AppPageHeader
        title="Observability & Hardening"
        subtitle="Operational controls: Alerting rules, cutover promotes, metrics exports, backups & GDPR pruning, performance scenarios, and tenant locale config."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/connectors" className="underline text-slate-600" data-testid="nav-connectors">
              Connectors
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/browser-profiles" className="underline text-slate-600" data-testid="nav-browser-profiles">
              Browser profiles
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/members" className="underline text-slate-600" data-testid="nav-members">
              Members & invitations
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/audit-log" className="underline text-slate-600" data-testid="nav-audit-log">
              Audit log
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/observability" className="underline text-slate-600 font-semibold text-slate-900" data-testid="nav-observability">
              Observability
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/webhooks" className="underline text-slate-600" data-testid="nav-webhooks">
              Webhooks
            </Link>
            <Settings2 className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        {error ? (
          <div className="mb-4 p-3 text-sm border border-rose-200 bg-rose-50 text-rose-700 rounded-sm font-mono flex items-start gap-2">
            <AlertTriangle className="size-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        ) : null}

        {/* Premium Tab bar navigation */}
        <div className="flex border-b border-slate-200 gap-1 overflow-x-auto mb-6 bg-slate-50 p-1 rounded-sm shadow-inner">
          <button
            onClick={() => setActiveTab("alerting")}
            data-testid="tab-alerting"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "alerting"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <Activity className="size-3.5" /> Alerts & Readiness
          </button>
          <button
            onClick={() => setActiveTab("cutover")}
            data-testid="tab-cutover"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "cutover"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <Shield className="size-3.5" /> Cutover
          </button>
          <button
            onClick={() => setActiveTab("health")}
            data-testid="tab-health"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "health"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <RefreshCw className="size-3.5" /> Connector Health
          </button>
          <button
            onClick={() => setActiveTab("metrics")}
            data-testid="tab-metrics"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "metrics"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <Globe className="size-3.5" /> Metrics Export
          </button>
          <button
            onClick={() => setActiveTab("backups")}
            data-testid="tab-backups"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "backups"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <Database className="size-3.5" /> Backups & GDPR
          </button>
          <button
            onClick={() => setActiveTab("performance")}
            data-testid="tab-performance"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "performance"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <LineChart className="size-3.5" /> Performance SLOs
          </button>
          <button
            onClick={() => setActiveTab("locale")}
            data-testid="tab-locale"
            className={`px-4 py-2 text-xs font-semibold rounded-sm tracking-wide transition-all duration-150 flex items-center gap-1.5 ${
              activeTab === "locale"
                ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                : "text-slate-500 hover:text-slate-800 hover:bg-white/40"
            }`}
          >
            <Globe className="size-3.5" /> Org Default Locale
          </button>
        </div>

        {loading ? (
          <div className="text-sm font-mono text-slate-500 py-8 flex items-center gap-2">
            <RefreshCw className="size-4 animate-spin text-slate-400" />
            Loading tab controls…
          </div>
        ) : (
          <div className="transition-all duration-200">
            {/* TAB 1: Alerting & Readiness */}
            {activeTab === "alerting" && (
              <div className="space-y-6" data-testid="panel-alerting">
                {summary && (
                  <AppSection title="Readiness Profile">
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      <div className="p-4 border rounded bg-white shadow-sm flex flex-col justify-between">
                        <div>
                          <div className="text-[10px] font-mono uppercase text-slate-500">Environment Mode</div>
                          <div className="text-base font-bold font-mono mt-1 text-slate-800" data-testid="readiness-env-mode">{summary.environment_mode}</div>
                        </div>
                        <div className="mt-2.5">
                          {summary.gate_passed ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200" data-testid="readiness-gate-status">
                              <CheckCircle2 className="size-3.5" /> gate passing
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-sm text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200" data-testid="readiness-gate-status">
                              <AlertTriangle className="size-3.5" /> gate blocked
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="p-4 border rounded bg-white shadow-sm">
                        <div className="text-[10px] font-mono uppercase text-slate-500">Backup Freshness</div>
                        <div className="text-base font-bold font-mono mt-1 text-slate-800" data-testid="readiness-backup-freshness">{summary.backup_freshness}</div>
                        <div className="text-xs text-slate-500 mt-2 font-mono" data-testid="readiness-backup-age">
                          {summary.backup_age_hours !== null
                            ? `${summary.backup_age_hours.toFixed(2)} h old`
                            : "no backup recorded"}
                        </div>
                      </div>
                      <div className="p-4 border rounded bg-white shadow-sm">
                        <div className="text-[10px] font-mono uppercase text-slate-500">Worker heartbeat</div>
                        <div className="text-base font-bold font-mono mt-1 text-slate-800" data-testid="readiness-worker-heartbeat">
                          {summary.worker_heartbeat_age_seconds !== null
                            ? `${Math.round(summary.worker_heartbeat_age_seconds)} s ago`
                            : "no heartbeat"}
                        </div>
                        <div className="text-xs text-slate-500 mt-2">Active background workers status</div>
                      </div>
                    </div>

                    {summary.gate_blocking.length > 0 ? (
                      <div className="mt-4 p-3 border border-rose-200 bg-rose-50/50 rounded text-xs space-y-1.5" data-testid="readiness-blocking-rules">
                        <div className="font-bold font-mono uppercase text-rose-800 flex items-center gap-1">
                          <AlertTriangle className="size-3.5 shrink-0" />
                          Blocking launch gate
                        </div>
                        <ul className="list-disc pl-5 font-mono text-rose-700">
                          {summary.gate_blocking.map((c) => (
                            <li key={c.name}>
                              <span className="font-semibold">{c.name}</span> — {c.detail}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    {summary.gate_warnings.length > 0 ? (
                      <div className="mt-4 p-3 border border-amber-200 bg-amber-50/50 rounded text-xs space-y-1.5">
                        <div className="font-bold font-mono uppercase text-amber-800 flex items-center gap-1">
                          <CircleAlert className="size-3.5 shrink-0" />
                          Gate Warnings
                        </div>
                        <ul className="list-disc pl-5 font-mono text-amber-700">
                          {summary.gate_warnings.map((c) => (
                            <li key={c.name}>
                              <span className="font-semibold">{c.name}</span> — {c.detail}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}

                    <div className="mt-4 text-xs font-mono flex flex-wrap gap-4 text-slate-600 bg-slate-50 p-2.5 rounded-sm border">
                      <span>Open Info Alerts: <strong>{openBySeverity.info ?? 0}</strong></span>
                      <span>Open Warning Alerts: <strong>{openBySeverity.warning ?? 0}</strong></span>
                      <span>Open Critical Alerts: <strong className="text-rose-600">{openBySeverity.critical ?? 0}</strong></span>
                      <span className="sm:ml-auto">Rules Status: <strong>{summary.rules_enabled}/{summary.rules_total}</strong> active</span>
                    </div>
                  </AppSection>
                )}

                <AppSection title="Alert Rules Configuration">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Rule Name</th>
                          <th className="px-4 py-3">Metric target</th>
                          <th className="px-4 py-3">Comparison threshold</th>
                          <th className="px-4 py-3">Window</th>
                          <th className="px-4 py-3">Severity</th>
                          <th className="px-4 py-3">Channels</th>
                          <th className="px-4 py-3">Enabled</th>
                          <th className="px-4 py-3"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {rules.map((rule) => (
                          <tr key={rule.id} className="hover:bg-slate-50/40" data-testid="rule-row">
                            <td className="px-4 py-2.5 font-bold text-slate-800">
                              {rule.name}
                              {rule.is_system ? (
                                <span className="ml-1.5 px-1.5 py-0.5 rounded bg-slate-100 text-[9px] font-semibold text-slate-500">SYSTEM</span>
                              ) : null}
                            </td>
                            <td className="px-4 py-2.5 text-slate-600">{rule.metric}</td>
                            <td className="px-4 py-2.5 text-slate-700">
                              {rule.operator} {rule.threshold}
                            </td>
                            <td className="px-4 py-2.5 text-slate-600">{rule.window_seconds}s</td>
                            <td className="px-4 py-2.5 font-sans">{severityBadge(rule.severity)}</td>
                            <td className="px-4 py-2.5 text-slate-600">{rule.channels.join(", ")}</td>
                            <td className="px-4 py-2.5">
                              <button
                                onClick={() => void onToggleRule(rule)}
                                className={`font-semibold underline tracking-wide ${rule.enabled ? 'text-emerald-700' : 'text-slate-400'}`}
                                disabled={rule.is_system}
                                data-testid="rule-toggle"
                              >
                                {rule.enabled ? "ACTIVE" : "DISABLED"}
                              </button>
                            </td>
                            <td className="px-4 py-2.5 text-right font-sans">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => void onDeleteRule(rule.id)}
                                disabled={rule.is_system}
                                data-testid="rule-delete"
                                className="h-7 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                              >
                                <Trash2 className="size-3" /> delete
                              </Button>
                            </td>
                          </tr>
                        ))}
                        {rules.length === 0 ? (
                          <tr>
                            <td colSpan={8} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No alert rules configured.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>

                  <div className="mt-6 p-4 border rounded bg-slate-50/70 shadow-sm" data-testid="rule-create-form">
                    <div className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1">
                      <ListChecks className="size-4 text-slate-500" />
                      Add Custom Alerting Rule
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <Label htmlFor="obs-name" className="text-[11px] font-mono uppercase text-slate-600">Rule Name</Label>
                        <Input
                          id="obs-name"
                          data-testid="rule-name"
                          value={newRule.name}
                          onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                          placeholder="e.g., custom.alert.latency"
                          className="mt-1 font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="obs-metric" className="text-[11px] font-mono uppercase text-slate-600">Metric</Label>
                        <select
                          id="obs-metric"
                          data-testid="rule-metric"
                          className="w-full px-2.5 py-1.5 mt-1 text-xs border rounded-sm bg-white font-mono h-9"
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
                        <Label htmlFor="obs-operator" className="text-[11px] font-mono uppercase text-slate-600">Operator</Label>
                        <select
                          id="obs-operator"
                          data-testid="rule-operator"
                          className="w-full px-2.5 py-1.5 mt-1 text-xs border rounded-sm bg-white font-mono h-9"
                          value={newRule.operator}
                          onChange={(e) => setNewRule({ ...newRule, operator: e.target.value })}
                        >
                          <option value="gt">gt (&gt;)</option>
                          <option value="gte">gte (&gt;=)</option>
                          <option value="lt">lt (&lt;)</option>
                          <option value="lte">lte (&lt;=)</option>
                          <option value="eq">eq (==)</option>
                        </select>
                      </div>
                      <div>
                        <Label htmlFor="obs-threshold" className="text-[11px] font-mono uppercase text-slate-600">Threshold</Label>
                        <Input
                          id="obs-threshold"
                          data-testid="rule-threshold"
                          type="number"
                          value={newRule.threshold}
                          onChange={(e) => setNewRule({ ...newRule, threshold: Number(e.target.value) })}
                          className="mt-1 font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="obs-window" className="text-[11px] font-mono uppercase text-slate-600">Window (s)</Label>
                        <Input
                          id="obs-window"
                          data-testid="rule-window"
                          type="number"
                          value={newRule.window_seconds}
                          onChange={(e) => setNewRule({ ...newRule, window_seconds: Number(e.target.value) })}
                          className="mt-1 font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="obs-severity" className="text-[11px] font-mono uppercase text-slate-600">Severity</Label>
                        <select
                          id="obs-severity"
                          data-testid="rule-severity"
                          className="w-full px-2.5 py-1.5 mt-1 text-xs border rounded-sm bg-white font-mono h-9"
                          value={newRule.severity}
                          onChange={(e) => setNewRule({ ...newRule, severity: e.target.value })}
                        >
                          <option value="info">info</option>
                          <option value="warning">warning</option>
                          <option value="critical">critical</option>
                        </select>
                      </div>
                      <div>
                        <Label htmlFor="obs-cooldown" className="text-[11px] font-mono uppercase text-slate-600">Cooldown (s)</Label>
                        <Input
                          id="obs-cooldown"
                          data-testid="rule-cooldown"
                          type="number"
                          value={newRule.cooldown_seconds}
                          onChange={(e) => setNewRule({ ...newRule, cooldown_seconds: Number(e.target.value) })}
                          className="mt-1 font-mono text-xs"
                        />
                      </div>
                      <div className="sm:col-span-2">
                        <Label htmlFor="obs-channels" className="text-[11px] font-mono uppercase text-slate-600">Export Channels (comma-separated)</Label>
                        <Input
                          id="obs-channels"
                          data-testid="rule-channels"
                          value={newRule.channels}
                          onChange={(e) => setNewRule({ ...newRule, channels: e.target.value })}
                          className="mt-1 font-mono text-xs"
                        />
                      </div>
                    </div>
                    <div className="mt-4 flex justify-end">
                      <Button
                        onClick={() => void onCreateRule()}
                        disabled={!newRule.name}
                        data-testid="rule-submit"
                        className="text-xs h-9"
                      >
                        Create Alert Rule
                      </Button>
                    </div>
                  </div>
                </AppSection>

                <AppSection title="Recent Triggered Events">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Fired timestamp</th>
                          <th className="px-4 py-3">Rule name</th>
                          <th className="px-4 py-3">Metric</th>
                          <th className="px-4 py-3">Alert status</th>
                          <th className="px-4 py-3">Severity</th>
                          <th className="px-4 py-3"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {events.map((event) => (
                          <tr key={event.id} className="hover:bg-slate-50/40" data-testid="event-row">
                            <td className="px-4 py-2.5 text-slate-600">{event.fired_at}</td>
                            <td className="px-4 py-2.5 font-bold text-slate-800">{event.rule_name}</td>
                            <td className="px-4 py-2.5 text-slate-500">{event.metric}</td>
                            <td className="px-4 py-2.5">{statusBadge(event.status)}</td>
                            <td className="px-4 py-2.5 font-sans">{severityBadge(event.severity)}</td>
                            <td className="px-4 py-2.5 text-right font-sans">
                              {event.status === "firing" ? (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => void onAcknowledgeEvent(event)}
                                  data-testid="event-acknowledge"
                                  className="h-7 border hover:bg-slate-50 text-slate-700"
                                >
                                  <ShieldCheck className="size-3.5" /> acknowledge
                                </Button>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                        {events.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No alert events generated yet.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </AppSection>
              </div>
            )}

            {/* TAB 2: Environment Cutover */}
            {activeTab === "cutover" && (
              <div className="space-y-6" data-testid="panel-cutover">
                {summary && (
                  <div className="p-4 border rounded bg-white shadow-sm flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">Current Execution Mode</h3>
                      <p className="text-xs text-slate-500">Status details of the production gate rules</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`size-3 rounded-full ${summary.gate_passed ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`}></span>
                      <span className="font-mono text-base font-bold text-slate-800" data-testid="cutover-current-mode">
                        {summary.environment_mode}
                      </span>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Enter Pilot Live */}
                  <div className="p-4 border rounded bg-white shadow-sm space-y-4" data-testid="cutover-promote-form">
                    <div className="flex items-center gap-1.5 font-bold text-sm text-slate-800 border-b pb-2">
                      <Zap className="size-4 text-amber-500" />
                      <span>Promote to Pilot Live</span>
                    </div>
                    <p className="text-xs text-slate-500">Run backend actions in real/pilot environment mode. Access keys needed.</p>
                    <div className="space-y-3">
                      <div>
                        <Label htmlFor="promote-reason" className="text-[10px] font-mono uppercase text-slate-600">Reason (Required)</Label>
                        <Input
                          id="promote-reason"
                          data-testid="promote-reason"
                          value={cutoverReason}
                          onChange={(e) => setCutoverReason(e.target.value)}
                          placeholder="Required justification..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="promote-notes" className="text-[10px] font-mono uppercase text-slate-600">Notes (Optional)</Label>
                        <Input
                          id="promote-notes"
                          data-testid="promote-notes"
                          value={cutoverNotes}
                          onChange={(e) => setCutoverNotes(e.target.value)}
                          placeholder="Operational details..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="promote-pin" className="text-[10px] font-mono uppercase text-slate-600">Security Admin PIN (Optional)</Label>
                        <Input
                          id="promote-pin"
                          data-testid="promote-pin"
                          type="password"
                          value={cutoverPin}
                          onChange={(e) => setCutoverPin(e.target.value)}
                          placeholder="e.g. 1234"
                          className="mt-1 text-xs"
                        />
                      </div>
                      <Button
                        type="button"
                        data-testid="promote-submit"
                        disabled={cutoverActionBusy || !cutoverReason}
                        onClick={() => void handleEnterPilotLive()}
                        className="w-full text-xs h-9 bg-slate-900 text-white hover:bg-slate-800"
                      >
                        Enter Pilot Live
                      </Button>
                    </div>
                  </div>

                  {/* Pause Environment */}
                  <div className="p-4 border rounded bg-white shadow-sm space-y-4" data-testid="cutover-pause-form">
                    <div className="flex items-center gap-1.5 font-bold text-sm text-slate-800 border-b pb-2">
                      <AlertCircle className="size-4 text-rose-500" />
                      <span>Pause Environment</span>
                    </div>
                    <p className="text-xs text-slate-500">Temporarily freeze all background discovery workers and scraper processes.</p>
                    <div className="space-y-3">
                      <div>
                        <Label htmlFor="pause-reason" className="text-[10px] font-mono uppercase text-slate-600">Reason (Required)</Label>
                        <Input
                          id="pause-reason"
                          data-testid="pause-reason"
                          value={cutoverReason}
                          onChange={(e) => setCutoverReason(e.target.value)}
                          placeholder="Emergency pause reason..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="pause-notes" className="text-[10px] font-mono uppercase text-slate-600">Notes (Optional)</Label>
                        <Input
                          id="pause-notes"
                          data-testid="pause-notes"
                          value={cutoverNotes}
                          onChange={(e) => setCutoverNotes(e.target.value)}
                          placeholder="Impact details..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div className="h-14"></div> {/* spacer */}
                      <Button
                        type="button"
                        data-testid="pause-submit"
                        disabled={cutoverActionBusy || !cutoverReason}
                        onClick={() => void handlePauseEnv()}
                        className="w-full text-xs h-9 bg-rose-600 hover:bg-rose-700 text-white"
                      >
                        Pause Services
                      </Button>
                    </div>
                  </div>

                  {/* Rollback/Restore Mode */}
                  <div className="p-4 border rounded bg-white shadow-sm space-y-4" data-testid="cutover-rollback-form">
                    <div className="flex items-center gap-1.5 font-bold text-sm text-slate-800 border-b pb-2">
                      <History className="size-4 text-blue-500" />
                      <span>Rollback Environment Mode</span>
                    </div>
                    <p className="text-xs text-slate-500">Revert execution environment back to test-mode or target stable sandbox profile.</p>
                    <div className="space-y-3">
                      <div>
                        <Label htmlFor="rollback-reason" className="text-[10px] font-mono uppercase text-slate-600">Reason (Required)</Label>
                        <Input
                          id="rollback-reason"
                          data-testid="rollback-reason"
                          value={cutoverReason}
                          onChange={(e) => setCutoverReason(e.target.value)}
                          placeholder="Reversion reason..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="rollback-notes" className="text-[10px] font-mono uppercase text-slate-600">Notes (Optional)</Label>
                        <Input
                          id="rollback-notes"
                          data-testid="rollback-notes"
                          value={cutoverNotes}
                          onChange={(e) => setCutoverNotes(e.target.value)}
                          placeholder="Notes..."
                          className="mt-1 text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="rollback-target" className="text-[10px] font-mono uppercase text-slate-600">Target Mode</Label>
                        <select
                          id="rollback-target"
                          data-testid="rollback-target"
                          value={cutoverRollbackMode}
                          onChange={(e) => setCutoverRollbackMode(e.target.value)}
                          className="w-full px-2 py-1.5 mt-1 border rounded-sm text-xs bg-white h-9"
                        >
                          <option value="test_like">test_like (Sandbox/Staging)</option>
                          <option value="paused">paused</option>
                          <option value="pilot_live">pilot_live</option>
                        </select>
                      </div>
                      <Button
                        type="button"
                        data-testid="rollback-submit"
                        disabled={cutoverActionBusy || !cutoverReason}
                        onClick={() => void handleRollbackEnv()}
                        className="w-full text-xs h-9 bg-blue-600 hover:bg-blue-700 text-white"
                      >
                        Execute Rollback
                      </Button>
                    </div>
                  </div>
                </div>

                <AppSection title="Audit: Environment Cutover History">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Timestamp</th>
                          <th className="px-4 py-3">Operator / Actor</th>
                          <th className="px-4 py-3">Transition</th>
                          <th className="px-4 py-3">Justification Reason</th>
                          <th className="px-4 py-3">Gate status</th>
                          <th className="px-4 py-3">Gate summary</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {cutoverEvents.map((evt) => (
                          <tr key={evt.event_id} className="hover:bg-slate-50/40" data-testid="cutover-event-row">
                            <td className="px-4 py-3 text-slate-500 whitespace-nowrap">{evt.occurred_at}</td>
                            <td className="px-4 py-3 font-semibold text-slate-800">{evt.actor}</td>
                            <td className="px-4 py-3 whitespace-nowrap text-slate-700">
                              {evt.previous_mode} &rarr; <strong className="text-slate-900">{evt.new_mode}</strong>
                            </td>
                            <td className="px-4 py-3 text-slate-600">
                              <div className="font-sans font-medium">{evt.reason}</div>
                              {evt.notes && <div className="text-[10px] text-slate-400 mt-0.5">Notes: {evt.notes}</div>}
                            </td>
                            <td className="px-4 py-3">
                              {evt.gate_passed ? (
                                <span className="text-emerald-700 font-semibold flex items-center gap-0.5">
                                  <CheckCircle2 className="size-3" /> PASS
                                </span>
                              ) : (
                                <span className="text-rose-700 font-semibold flex items-center gap-0.5">
                                  <AlertTriangle className="size-3" /> BLOCK
                                </span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-[10px] text-slate-500 max-w-xs truncate" title={evt.gate_summary}>
                              {evt.gate_summary}
                            </td>
                          </tr>
                        ))}
                        {cutoverEvents.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No environment transitions recorded in database.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </AppSection>
              </div>
            )}

            {/* TAB 3: Connector Health */}
            {activeTab === "health" && (
              <div className="space-y-6" data-testid="panel-health">
                <AppSection title="Connectors Health Status">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Connector / Source</th>
                          <th className="px-4 py-3">Type</th>
                          <th className="px-4 py-3">Health State</th>
                          <th className="px-4 py-3">Total Runs</th>
                          <th className="px-4 py-3">Success Rate</th>
                          <th className="px-4 py-3">Last re-compute time</th>
                          <th className="px-4 py-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {connectorHealth.map((item) => {
                          const status = item.snapshot ? item.snapshot.status : "unknown";
                          const totalRuns = item.snapshot ? item.snapshot.total_runs : 0;
                          const successRate = item.snapshot ? `${(item.snapshot.success_rate * 100).toFixed(1)}%` : "100.0%";
                          const computedAt = item.snapshot ? item.snapshot.computed_at : "Never";
                          return (
                            <tr key={item.source_id} className="hover:bg-slate-50/40" data-testid="connector-health-row">
                              <td className="px-4 py-3 font-semibold text-slate-800">{item.source_name}</td>
                              <td className="px-4 py-3 text-slate-500 uppercase">{item.connector_type}</td>
                              <td className="px-4 py-3">
                                {status === "healthy" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold" data-testid="health-badge">
                                    HEALTHY
                                  </span>
                                )}
                                {status === "degraded" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-bold" data-testid="health-badge">
                                    DEGRADED
                                  </span>
                                )}
                                {status === "down" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold" data-testid="health-badge">
                                    DOWN
                                  </span>
                                )}
                                {status !== "healthy" && status !== "degraded" && status !== "down" && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm bg-slate-100 text-slate-600 border border-slate-200 text-[10px]" data-testid="health-badge">
                                    {status.toUpperCase()}
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-slate-600">{totalRuns}</td>
                              <td className="px-4 py-3 text-slate-600">{successRate}</td>
                              <td className="px-4 py-3 text-slate-500">{computedAt}</td>
                              <td className="px-4 py-3 text-slate-600 flex gap-2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={connectorActionBusy}
                                  onClick={() => void handleComputeHealthSnapshot(item.source_id)}
                                  data-testid="health-compute"
                                  className="h-7 border border-slate-200 hover:bg-slate-50"
                                >
                                  <RefreshCw className="size-3" /> Compute
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  disabled={connectorActionBusy}
                                  onClick={() => void handleViewHealthErrors(item.source_id)}
                                  data-testid="health-errors"
                                  className="h-7 border border-slate-200 hover:bg-slate-50 text-slate-700"
                                >
                                  <Eye className="size-3" /> Errors
                                </Button>
                              </td>
                            </tr>
                          );
                        })}
                        {connectorHealth.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No registered connectors found to report health.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>

                  {healthErrorLogs && (
                    <div className="p-4 border border-rose-200 bg-rose-50/20 rounded shadow-sm space-y-2 mt-4" data-testid="health-error-details">
                      <div className="flex items-center justify-between border-b border-rose-100 pb-2">
                        <div className="font-bold text-sm text-slate-800 font-mono">
                          Recent Errors: {healthErrorLogs.source_id}
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setHealthErrorLogs(null)}
                          className="h-6 text-xs text-slate-500"
                        >
                          Close
                        </Button>
                      </div>
                      <div className="space-y-2 max-h-60 overflow-y-auto">
                        {healthErrorLogs.errors.map((err: any, idx: number) => (
                          <div key={idx} className="p-3 bg-white border border-rose-100 rounded text-xs font-mono">
                            <div className="flex justify-between text-slate-400 mb-1 text-[10px]">
                              <span>Timestamp: {err.occurred_at}</span>
                              <span className="font-semibold text-rose-700">Code: {err.error_code}</span>
                            </div>
                            <div className="text-slate-800 font-medium">{err.message}</div>
                            {err.detail && <div className="text-[10px] text-slate-500 mt-1 bg-slate-50 p-1.5 rounded">{err.detail}</div>}
                          </div>
                        ))}
                        {healthErrorLogs.errors.length === 0 ? (
                          <p className="text-xs text-slate-500 font-sans py-2">No errors logged for this connector.</p>
                        ) : null}
                      </div>
                    </div>
                  )}
                </AppSection>
              </div>
            )}

            {/* TAB 4: Metrics Export Policy */}
            {activeTab === "metrics" && (
              <div className="space-y-6" data-testid="panel-metrics">
                <AppSection title="Prometheus & Sentry Export Pipelines">
                  <div className="p-4 border rounded bg-white shadow-sm max-w-xl space-y-4" data-testid="metrics-form">
                    {metricsSuccessMsg && (
                      <div className="p-2.5 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded font-semibold">
                        {metricsSuccessMsg}
                      </div>
                    )}
                    <div className="space-y-4">
                      <div>
                        <Label htmlFor="metrics-cidr" className="text-xs font-bold text-slate-700">Prometheus Allowed CIDRs (comma-separated)</Label>
                        <p className="text-[10px] text-slate-500 mb-1">Restricts access to scraping metrics</p>
                        <Input
                          id="metrics-cidr"
                          data-testid="metrics-cidr"
                          value={metricsPolicy.prometheus_cidr_blocks}
                          onChange={(e) => setMetricsPolicy({ ...metricsPolicy, prometheus_cidr_blocks: e.target.value })}
                          placeholder="e.g. 127.0.0.1/32, 192.168.1.0/24"
                          className="font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="metrics-token" className="text-xs font-bold text-slate-700">Prometheus Scrape Bearer Token</Label>
                        <p className="text-[10px] text-slate-500 mb-1">Required authorization header token for scraper</p>
                        <Input
                          id="metrics-token"
                          data-testid="metrics-token"
                          type="text"
                          value={metricsPolicy.prometheus_scrape_token}
                          onChange={(e) => setMetricsPolicy({ ...metricsPolicy, prometheus_scrape_token: e.target.value })}
                          placeholder="e.g. secret-scrape-bearer-token"
                          className="font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="sentry-dsn" className="text-xs font-bold text-slate-700">Sentry DSN (Data Source Name)</Label>
                        <p className="text-[10px] text-slate-500 mb-1">Error collection endpoints connection string</p>
                        <Input
                          id="sentry-dsn"
                          data-testid="metrics-sentry-dsn"
                          value={metricsPolicy.sentry_dsn}
                          onChange={(e) => setMetricsPolicy({ ...metricsPolicy, sentry_dsn: e.target.value })}
                          placeholder="https://public@sentry.io/1234"
                          className="font-mono text-xs"
                        />
                      </div>
                      <div>
                        <Label htmlFor="sentry-env" className="text-xs font-bold text-slate-700">Sentry Environment Name</Label>
                        <Input
                          id="sentry-env"
                          data-testid="metrics-sentry-env"
                          value={metricsPolicy.sentry_environment}
                          onChange={(e) => setMetricsPolicy({ ...metricsPolicy, sentry_environment: e.target.value })}
                          placeholder="production"
                          className="font-mono text-xs"
                        />
                      </div>

                      <div className="flex gap-2 pt-2">
                        <Button
                          type="button"
                          data-testid="metrics-save"
                          disabled={metricsActionBusy}
                          onClick={() => void handleSaveMetricsPolicy()}
                          className="text-xs h-9 bg-slate-900 text-white"
                        >
                          Save Export Policy
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          data-testid="metrics-test"
                          disabled={metricsActionBusy}
                          onClick={() => void handleTestMetricsConnection()}
                          className="text-xs h-9 border border-slate-200"
                        >
                          Test connection
                        </Button>
                      </div>
                    </div>
                  </div>
                </AppSection>
              </div>
            )}

            {/* TAB 5: Backups & GDPR Retention */}
            {activeTab === "backups" && (
              <div className="space-y-6" data-testid="panel-backups">
                {/* Backups List and Actions */}
                <AppSection title="Backup Snapshot Snapshots">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm mb-4">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Backup snapshot ID</th>
                          <th className="px-4 py-3">Creation Date</th>
                          <th className="px-4 py-3">Verification state</th>
                          <th className="px-4 py-3">DB Size</th>
                          <th className="px-4 py-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {backups.map((snap) => (
                          <tr key={snap.backup_id} className="hover:bg-slate-50/40" data-testid="backup-snapshot-row">
                            <td className="px-4 py-3 font-semibold text-slate-800">{snap.backup_id}</td>
                            <td className="px-4 py-3 text-slate-500">{snap.created_at}</td>
                            <td className="px-4 py-3">
                              <select
                                value={snap.verification_status}
                                onChange={(e) => void handleVerifyBackup(snap.backup_id, e.target.value)}
                                disabled={backupsBusy}
                                className="border rounded px-1.5 py-0.5 text-xs bg-transparent"
                                data-testid="backup-verify-select"
                              >
                                <option value="recorded">RECORDED</option>
                                <option value="verified_restore">VERIFIED_RESTORE</option>
                                <option value="verified_rehearsal">VERIFIED_REHEARSAL</option>
                                <option value="invalid">INVALID</option>
                              </select>
                            </td>
                            <td className="px-4 py-3 text-slate-600">{(snap.database_size_bytes / 1024).toFixed(1)} KB</td>
                            <td className="px-4 py-3 flex gap-2">
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={backupsBusy}
                                onClick={() => void handleDryRunRestore(snap.backup_id)}
                                data-testid="backup-dry-run"
                                className="h-7 border hover:bg-slate-50 text-slate-700"
                              >
                                Dry-run Restore
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={backupsBusy}
                                onClick={() => void handleRehearsalRestore(snap.backup_id)}
                                data-testid="backup-rehearsal"
                                className="h-7 border hover:bg-slate-50 text-slate-700"
                              >
                                Rehearsal
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={backupsBusy}
                                onClick={() => void handleRealRestore(snap.backup_id)}
                                data-testid="backup-restore"
                                className="h-7 bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200"
                              >
                                Real Restore
                              </Button>
                            </td>
                          </tr>
                        ))}
                        {backups.length === 0 ? (
                          <tr>
                            <td colSpan={5} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No backup snapshots recorded in system database.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>

                  {restoreDryRunResult && (
                    <div className="p-4 border border-blue-200 bg-blue-50/30 rounded font-mono text-xs space-y-2 mt-4" data-testid="backup-dry-run-results">
                      <div className="font-bold text-sm text-slate-800">Dry-Run Restore Results: {restoreDryRunResult.backup_id}</div>
                      <div>Status: <span className="font-semibold text-blue-700">{restoreDryRunResult.status}</span></div>
                      <div>Target location: <code>{restoreDryRunResult.target_location}</code></div>
                      <div>Manifest MD5 Hash: <code>{restoreDryRunResult.manifest_hash}</code></div>
                      <div className="font-bold text-slate-900" data-testid="backup-dry-run-row-count">
                        Restored Row Count: {restoreDryRunResult.row_count}
                      </div>
                      {restoreDryRunResult.error && <div className="text-rose-700 mt-1">Error: {restoreDryRunResult.error}</div>}
                    </div>
                  )}

                  {restoreResult && (
                    <div className="p-4 border border-emerald-200 bg-emerald-50/30 rounded font-mono text-xs space-y-2 mt-4">
                      <div className="font-bold text-sm text-emerald-800">Real Restore Completed!</div>
                      <div>Backup ID: <code>{restoreResult.backup_id}</code></div>
                      <div>Status: <strong>{restoreResult.status}</strong></div>
                      <div>Restored Row Count: <strong>{restoreResult.row_count}</strong></div>
                    </div>
                  )}
                </AppSection>

                {/* Retention Policy settings */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <AppSection title="Backup & Audit Log Retention">
                    <div className="p-4 border rounded bg-white shadow-sm space-y-4" data-testid="retention-form">
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="ret-backup" className="text-xs font-bold text-slate-700">Backup snapshot retention (days)</Label>
                          <Input
                            id="ret-backup"
                            data-testid="retention-backups-days"
                            type="number"
                            value={retentionPolicy.backup_retention_days}
                            onChange={(e) => setRetentionPolicy({ ...retentionPolicy, backup_retention_days: Number(e.target.value) })}
                            className="mt-1 font-mono text-xs"
                          />
                        </div>
                        <div>
                          <Label htmlFor="ret-audit" className="text-xs font-bold text-slate-700">Audit log retention (days)</Label>
                          <Input
                            id="ret-audit"
                            data-testid="retention-audit-days"
                            type="number"
                            value={retentionPolicy.audit_retention_days}
                            onChange={(e) => setRetentionPolicy({ ...retentionPolicy, audit_retention_days: Number(e.target.value) })}
                            className="mt-1 font-mono text-xs"
                          />
                        </div>
                        <div className="flex items-center gap-2 pt-1">
                          <input
                            id="ret-prune"
                            data-testid="retention-prune-enabled"
                            type="checkbox"
                            checked={retentionPolicy.prune_enabled}
                            onChange={(e) => setRetentionPolicy({ ...retentionPolicy, prune_enabled: e.target.checked })}
                            className="rounded border-slate-300"
                          />
                          <Label htmlFor="ret-prune" className="text-xs text-slate-700 cursor-pointer">Enable automatic background pruning</Label>
                        </div>

                        <div className="flex gap-2 pt-2">
                          <Button
                            type="button"
                            data-testid="retention-submit"
                            disabled={backupsBusy}
                            onClick={() => void handleSaveRetentionPolicy()}
                            className="text-xs h-9 bg-slate-900 text-white"
                          >
                            Save Retention Settings
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            disabled={backupsBusy}
                            onClick={() => void handlePruneBackups()}
                            className="text-xs h-9 border text-rose-600 border-rose-200 hover:bg-rose-50"
                          >
                            Execute Prune Now
                          </Button>
                        </div>
                      </div>
                    </div>
                  </AppSection>

                  {/* GDPR Data Deletion */}
                  <AppSection title="GDPR Governance: Explicit Data Deletion">
                    <div className="p-4 border rounded bg-white shadow-sm space-y-4" data-testid="gdpr-form">
                      {gdprSuccessMsg && (
                        <div className="p-2.5 text-xs text-emerald-800 bg-emerald-50 border border-emerald-200 rounded font-semibold">
                          {gdprSuccessMsg}
                        </div>
                      )}
                      <div className="space-y-3">
                        <div>
                          <Label htmlFor="gdpr-target" className="text-xs font-bold text-slate-700">Deletion Target Entity</Label>
                          <select
                            id="gdpr-target"
                            data-testid="gdpr-target"
                            value={gdprTarget}
                            onChange={(e) => setGdprTarget(e.target.value)}
                            className="w-full px-2.5 py-1.5 mt-1 border rounded-sm text-xs bg-white h-9"
                          >
                            <option value="lead">Lead details & event associations</option>
                            <option value="user">User account and session history</option>
                          </select>
                        </div>
                        <div>
                          <Label htmlFor="gdpr-target-id" className="text-xs font-bold text-slate-700">Target Entity Database ID</Label>
                          <Input
                            id="gdpr-target-id"
                            data-testid="gdpr-target-id"
                            value={gdprTargetId}
                            onChange={(e) => setGdprTargetId(e.target.value)}
                            placeholder="e.g. user-uuid-1234"
                            className="mt-1 font-mono text-xs"
                          />
                        </div>
                        <div>
                          <Label htmlFor="gdpr-accepted-by" className="text-xs font-bold text-slate-700">Compliance officer approval name</Label>
                          <Input
                            id="gdpr-accepted-by"
                            data-testid="gdpr-accepted-by"
                            value={gdprAcceptedBy}
                            onChange={(e) => setGdprAcceptedBy(e.target.value)}
                            placeholder="e.g. compliance@example.com"
                            className="mt-1 text-xs"
                          />
                        </div>
                        <div>
                          <Label htmlFor="gdpr-reason" className="text-xs font-bold text-slate-700">Deletion Reason / GDPR request token</Label>
                          <Input
                            id="gdpr-reason"
                            data-testid="gdpr-reason"
                            value={gdprReason}
                            onChange={(e) => setGdprReason(e.target.value)}
                            placeholder="e.g. Customer requested deletion via support token #449"
                            className="mt-1 text-xs"
                          />
                        </div>

                        <Button
                          type="button"
                          data-testid="gdpr-submit"
                          disabled={backupsBusy || !gdprTargetId || !gdprAcceptedBy || !gdprReason}
                          onClick={() => void handleGdprDeletion()}
                          className="w-full text-xs h-9 bg-rose-600 text-white hover:bg-rose-700"
                        >
                          Execute Hard Redaction & Deletion
                        </Button>
                      </div>
                    </div>
                  </AppSection>
                </div>
              </div>
            )}

            {/* TAB 6: System Performance */}
            {activeTab === "performance" && (
              <div className="space-y-6" data-testid="panel-performance">
                <AppSection title="SLO Thresholds Diagnostics">
                  <div className="overflow-x-auto border rounded bg-white shadow-sm mb-6">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left bg-slate-50 text-[10px] font-mono uppercase text-slate-500 border-b">
                          <th className="px-4 py-3">Scenario</th>
                          <th className="px-4 py-3">Metric Name</th>
                          <th className="px-4 py-3">Last run p95 latency</th>
                          <th className="px-4 py-3">SLO Target Budget</th>
                          <th className="px-4 py-3">Evaluation window</th>
                          <th className="px-4 py-3">SLO status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-xs">
                        {perfSummary.map((item) => (
                          <tr key={item.scenario} className="hover:bg-slate-50/40" data-testid="performance-slo-row">
                            <td className="px-4 py-3 font-semibold text-slate-800">{item.scenario}</td>
                            <td className="px-4 py-3 text-slate-500">{item.metric}</td>
                            <td className="px-4 py-3 text-slate-700" data-testid="slo-actual-p95">
                              {item.snapshot ? `${item.snapshot.p95_ms.toFixed(1)} ms` : "No runs recorded"}
                            </td>
                            <td className="px-4 py-3 text-slate-600">{item.budget_p95_ms} ms</td>
                            <td className="px-4 py-3 text-slate-500">{item.window_seconds}s</td>
                            <td className="px-4 py-3" data-testid="slo-status">
                              {item.breach ? (
                                <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-sm bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold">
                                  BREACHED
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-sm bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-bold">
                                  COMPLIANT
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                        {perfSummary.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-8 text-center text-slate-400 font-sans">
                              No performance diagnostics baselines built.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>

                  <div className="p-4 border rounded bg-white shadow-sm max-w-xl space-y-4" data-testid="perf-run-form">
                    <div className="font-bold text-sm text-slate-800 flex items-center gap-1.5">
                      <Play className="size-4 text-emerald-500" />
                      <span>Run Load Scenarios Simulation</span>
                    </div>
                    <p className="text-xs text-slate-500">Inject traffic simulation to calculate the latency metrics baselines against the defined targets.</p>
                    <div className="flex flex-wrap gap-2 items-end">
                      <div className="flex-1 min-w-[240px]">
                        <Label htmlFor="perf-scenarios" className="text-[10px] font-mono uppercase text-slate-600">Performance Scenario</Label>
                        <select
                          id="perf-scenarios"
                          data-testid="perf-scenarios-select"
                          value={perfScenarioToRun}
                          onChange={(e) => setPerfScenarioToRun(e.target.value)}
                          className="w-full px-2.5 py-1.5 mt-1 border rounded-sm text-xs bg-white h-9"
                        >
                          <option value="api_read_latency">api_read_latency</option>
                          <option value="event_list_pagination">event_list_pagination</option>
                          <option value="discovery_first_progress">discovery_first_progress</option>
                        </select>
                      </div>
                      <Button
                        type="button"
                        data-testid="perf-run-submit"
                        disabled={perfActionBusy}
                        onClick={() => void handleRunPerfScenario()}
                        className="text-xs h-9 bg-slate-900 text-white"
                      >
                        {perfActionBusy ? "Simulating..." : "Execute Simulation"}
                      </Button>
                    </div>

                    {perfRunResult && (
                      <div className="p-4 border border-emerald-200 bg-emerald-50/30 rounded font-mono text-xs space-y-2 mt-4" data-testid="perf-run-results">
                        <div className="font-bold text-sm text-slate-850">Load Scenario Run Results: {perfRunResult.scenario}</div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] pt-1">
                          <div className="border bg-white p-2 rounded">
                            <span className="text-[9px] text-slate-400 block uppercase">p50 Latency</span>
                            <strong className="text-slate-800 text-xs">{perfRunResult.p50_ms.toFixed(1)} ms</strong>
                          </div>
                          <div className="border bg-white p-2 rounded" data-testid="perf-run-p95">
                            <span className="text-[9px] text-slate-400 block uppercase">p95 Latency</span>
                            <strong className="text-slate-800 text-xs">{perfRunResult.p95_ms.toFixed(1)} ms</strong>
                          </div>
                          <div className="border bg-white p-2 rounded">
                            <span className="text-[9px] text-slate-400 block uppercase">p99 Latency</span>
                            <strong className="text-slate-800 text-xs">{perfRunResult.p99_ms.toFixed(1)} ms</strong>
                          </div>
                          <div className="border bg-white p-2 rounded">
                            <span className="text-[9px] text-slate-400 block uppercase">Total Users</span>
                            <strong className="text-slate-800 text-xs">{perfRunResult.concurrent_users}</strong>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </AppSection>
              </div>
            )}

            {/* TAB 7: Organization Locale */}
            {activeTab === "locale" && (
              <div className="space-y-6" data-testid="panel-locale">
                <AppSection title="Organization Default Settings">
                  {session?.organization_id ? (
                    <div className="max-w-xl">
                      <OrganizationLocalePanel organizationId={session.organization_id} />
                    </div>
                  ) : (
                    <div className="text-sm font-mono text-slate-500">
                      No organization context found to display settings panel.
                    </div>
                  )}
                </AppSection>
              </div>
            )}
          </div>
        )}
      </div>
    </AppPageShell>
  );
}

export default AdminObservabilityPage;
