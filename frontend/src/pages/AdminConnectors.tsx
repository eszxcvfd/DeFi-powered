import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  approveCompliance,
  approveOwnerAdmin,
  getCloakBrowserPolicy,
  requestCloakBrowser,
  revokeCloakBrowser,
} from "@/api/cloakbrowserPolicy";
import { createConnector, listConnectors } from "@/api/connectors";
import {
  createAutoDisableRule,
  deleteAutoDisableRule,
  evaluateAutoDisable,
  listAutoDisableChoices,
  listAutoDisableEvents,
  listAutoDisableRules,
  recoverAutoDisableEvent,
  type AutoDisableChoices,
  type AutoDisableEventView,
  type AutoDisableRuleView,
  type AutoDisableTriggerValue,
} from "@/api/autoDisable";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { LIST_PAGE_SIZE } from "@/constants/listPageSize";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { CloakBrowserPolicyView } from "@/types/cloakbrowserPolicy";
import type { ConnectorView } from "@/types/connector";
import { Plus, ShieldAlert, Key, Chrome, Rss, Link2, Settings2, Database, ShieldCheck, Trash2, Activity, RefreshCcw, Info, Power } from "lucide-react";

export default function AdminConnectors() {
  const [items, setItems] = useState<ConnectorView[]>([]);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [page, setPage] = useState(1);
  const [cloakSourceId, setCloakSourceId] = useState<string | null>(null);
  const [cloakPolicy, setCloakPolicy] = useState<CloakBrowserPolicyView | null>(null);
  const [cloakRationale, setCloakRationale] = useState("");

  // Auto-disable states
  const [autoSourceId, setAutoSourceId] = useState<string | null>(null);
  const [autoRules, setAutoRules] = useState<AutoDisableRuleView[]>([]);
  const [autoEvents, setAutoEvents] = useState<AutoDisableEventView[]>([]);
  const [autoChoices, setAutoChoices] = useState<AutoDisableChoices | null>(null);
  const [autoMessage, setAutoMessage] = useState("");
  const [autoRecoveryReason, setAutoRecoveryReason] = useState("");

  // Rule creation states
  const [ruleTrigger, setRuleTrigger] = useState<AutoDisableTriggerValue>("health_unhealthy");
  const [ruleThreshold, setRuleThreshold] = useState("0.0");
  const [ruleWindow, setRuleWindow] = useState("1800");
  const [ruleConsecutive, setRuleConsecutive] = useState("3");
  const [ruleCooldown, setRuleCooldown] = useState("900");
  const [ruleEnabled, setRuleEnabled] = useState(true);

  async function refresh() {
    setItems(await listConnectors());
  }

  async function refreshAutoDisable() {
    if (!autoSourceId) {
      setAutoRules([]);
      setAutoEvents([]);
      return;
    }
    try {
      const rulesRes = await listAutoDisableRules(autoSourceId);
      setAutoRules(rulesRes.items);
      const eventsRes = await listAutoDisableEvents(autoSourceId);
      setAutoEvents(eventsRes.items);
    } catch (err: any) {
      console.error("Failed to load auto-disable data:", err);
      setAutoMessage(err?.message || "Failed to load auto-disable policies.");
    }
  }

  useEffect(() => {
    void refresh();
    void listAutoDisableChoices().then(setAutoChoices).catch(console.error);
  }, []);

  useEffect(() => {
    void refreshAutoDisable();
  }, [autoSourceId]);

  const selectedConnector = items.find((c) => c.id === autoSourceId);

  const triggersList = autoChoices?.triggers || [
    { value: "health_unhealthy", label: "Unhealthy Health Status" },
    { value: "captcha_rate_breach", label: "CAPTCHA Rate Breach" },
    { value: "failure_rate_breach", label: "Failure Rate Breach" },
    { value: "needs_user_action_storm", label: "User Action Storm" },
    { value: "error_spike", label: "Error Rate Spike" },
    { value: "manual_kill_switch", label: "Manual Kill Switch" },
  ];

  async function handleCreateRule() {
    if (!autoSourceId) {
      setAutoMessage("No connector selected.");
      return;
    }
    try {
      const thresholdVal = parseFloat(ruleThreshold);
      if (isNaN(thresholdVal)) {
        setAutoMessage("Invalid threshold value");
        return;
      }
      const windowSec = parseInt(ruleWindow);
      const consecutive = parseInt(ruleConsecutive);
      const cooldownSec = parseInt(ruleCooldown);

      await createAutoDisableRule({
        source_id: autoSourceId,
        trigger: ruleTrigger,
        threshold_value: thresholdVal,
        window_seconds: isNaN(windowSec) ? undefined : windowSec,
        consecutive_breaches: isNaN(consecutive) ? undefined : consecutive,
        cooldown_seconds: isNaN(cooldownSec) ? undefined : cooldownSec,
        enabled: ruleEnabled,
      });

      setAutoMessage("Rule created successfully.");
      void refreshAutoDisable();
      
      setRuleThreshold("0.0");
      setRuleWindow("1800");
      setRuleConsecutive("3");
      setRuleCooldown("900");
      setRuleEnabled(true);
    } catch (err: any) {
      setAutoMessage(err?.message || "Failed to create rule.");
    }
  }

  async function handleRecoverEvent(eventId: string) {
    if (!autoRecoveryReason.trim()) {
      setAutoMessage("Recovery reason required");
      return;
    }
    try {
      await recoverAutoDisableEvent(eventId, autoRecoveryReason);
      setAutoMessage("Recovery initiated successfully.");
      setAutoRecoveryReason("");
      void refreshAutoDisable();
      void refresh(); // refresh connector registry states too
    } catch (err: any) {
      setAutoMessage(err?.message || "Failed to initiate recovery.");
    }
  }

  async function handleComputeEvaluation() {
    if (!autoSourceId) {
      setAutoMessage("No connector selected.");
      return;
    }
    try {
      const result = await evaluateAutoDisable(autoSourceId);
      setAutoMessage(
        result.should_disable
          ? `Disabling trigger active: ${result.trigger} (${result.reason})`
          : "Evaluation complete: Connector health is within limits (no triggers fired)."
      );
      void refreshAutoDisable();
      void refresh(); // refresh connector registry states too
    } catch (err: any) {
      setAutoMessage(err?.message || "Failed to compute evaluation.");
    }
  }

  const currentItems = paginateSlice(items, page);

  async function addRss() {
    const newConn = await createConnector({
      name: name || "Events RSS",
      domain: domain || "events.example.com",
      connector_type: "rss",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", quota_per_day: 500, quota_used_today: 0, valid: true },
    });
    setName("");
    setDomain("");
    
    // Fetch updated list of connectors
    const updatedItems = await listConnectors();
    setItems(updatedItems);

    // Find the index of the newly created connector in the updated list
    const index = updatedItems.findIndex(item => item.id === newConn.id);
    if (index !== -1) {
      // Calculate which page this index corresponds to
      const targetPage = Math.floor(index / LIST_PAGE_SIZE) + 1;
      setPage(targetPage);
    }
  }

  const getConnectorIcon = (type: string) => {
    switch (type) {
      case "rss":
        return <Rss className="size-3.5 text-amber-600" />;
      case "playwright":
      case "browser":
        return <Chrome className="size-3.5 text-blue-600" />;
      default:
        return <Link2 className="size-3.5 text-slate-500" />;
    }
  };

  const getPolicyStateBadge = (state: string) => {
    const isApproved = state === "approved" || state === "valid" || state === "active";
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-sm text-xs font-mono border ${
        isApproved
          ? "bg-emerald-50 text-emerald-700 border-emerald-200" 
          : "bg-amber-50 text-amber-700 border-amber-200"
      }`}>
        {isApproved ? <ShieldCheck className="size-3.5" /> : <ShieldAlert className="size-3.5" />}
        {state}
      </span>
    );
  };

  const getEventStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200 uppercase font-mono">
            <span className="size-1.5 rounded-full bg-red-500 animate-pulse" />
            Active Alert
          </span>
        );
      case "recovering":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 uppercase font-mono">
            <span className="size-1.5 rounded-full bg-amber-500 animate-bounce" />
            Recovering
          </span>
        );
      case "resolved":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase font-mono">
            <span className="size-1.5 rounded-full bg-emerald-500" />
            Resolved
          </span>
        );
      case "superseded":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm text-[10px] font-semibold bg-slate-50 text-slate-600 border border-slate-200 uppercase font-mono">
            Superseded
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] font-semibold bg-slate-50 text-slate-700 border border-slate-200 uppercase font-mono">
            {status}
          </span>
        );
    }
  };

  return (
    <AppPageShell testId="admin-connectors">
      <AppPageHeader
        title="Connector registry"
        subtitle="Governance and connector policy — no live discovery from this screen."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/connectors" className="underline text-slate-600 font-semibold text-slate-900" data-testid="nav-connectors">
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
            <Link to="/admin/observability" className="underline text-slate-600" data-testid="nav-observability">
              Observability
            </Link>
            <Settings2 className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-4">
        <AppSection title="Add connector">
          
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-semibold text-slate-700">Connector Name</Label>
              <Input 
                data-testid="connector-name" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. TechNews Feed"
                className="mt-1.5 text-sm"
              />
            </div>
            <div>
              <Label className="text-sm font-semibold text-slate-700">Domain URL</Label>
              <Input 
                data-testid="connector-domain" 
                value={domain} 
                onChange={(e) => setDomain(e.target.value)} 
                placeholder="e.g. feed.technews.com"
                className="mt-1.5 text-sm"
              />
            </div>
            
            <Button 
              type="button" 
              data-testid="connector-add" 
              onClick={() => void addRss()}
              className="w-full rounded-sm text-sm font-semibold h-10 flex items-center justify-center gap-1.5"
            >
              <Plus className="size-4.5" strokeWidth={2.5} />
              Add RSS Source
            </Button>
          </div>
        </AppSection>
        </div>

        <div className="xl:col-span-8">
        <AppSection title="Registered connectors" className="flex flex-col">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-xs">
                  <th className="px-5 py-3 font-semibold">Name</th>
                  <th className="px-5 py-3 font-semibold">Type</th>
                  <th className="px-5 py-3 font-semibold">State</th>
                  <th className="px-5 py-3 font-semibold">Secret</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentItems.map((c) => {
                  const isSelected = autoSourceId === c.id;
                  return (
                    <tr
                      key={c.id}
                      className={`hover:bg-slate-50/20 transition-colors cursor-pointer ${
                        isSelected ? "bg-slate-100/70 border-l-2 border-l-blue-600" : ""
                      }`}
                      data-testid="connector-row"
                      onClick={() => {
                        setAutoSourceId(c.id);
                        if (c.automation_engine === "cloakbrowser") {
                          setCloakSourceId(c.id);
                          void getCloakBrowserPolicy(c.id).then(setCloakPolicy).catch(() => setCloakPolicy(null));
                        } else {
                          setCloakSourceId(null);
                          setCloakPolicy(null);
                        }
                      }}
                    >
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        <div className="flex flex-col">
                          <span>{c.name}</span>
                          <span className="text-xs text-slate-400 font-mono font-normal mt-0.5">{c.domain}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase">
                          {getConnectorIcon(c.connector_type)}
                          {c.connector_type}
                        </span>
                      </td>
                      <td className="px-5 py-4" data-testid="connector-policy-state">
                        {getPolicyStateBadge(c.policy_state)}
                      </td>
                      <td className="px-5 py-4 text-slate-500 font-mono text-xs" data-testid="connector-secret">
                        <span className="inline-flex items-center gap-1.5">
                          <Key className="size-3.5 text-slate-400" />
                          {c.secret_display || "(none)"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-10 text-center text-slate-400">
                      <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                      <span>No connectors registered yet.</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

          <ListPagination page={page} totalItems={items.length} onPageChange={setPage} testId="admin-connectors-pagination" />

          {cloakSourceId && (
            <div
              className="mt-6 border border-slate-200 rounded-sm p-5 bg-slate-50/40"
              data-testid="cloakbrowser-policy-panel"
            >
              <h3 className="text-sm font-semibold text-slate-800 mb-2">CloakBrowser governance</h3>
              {cloakPolicy ? (
                <>
                  <p className="text-xs font-mono text-slate-600 mb-3" data-testid="cloakbrowser-policy-state">
                    state: {cloakPolicy.policy_state} · runtime: {cloakPolicy.runtime_status}
                    {cloakPolicy.kill_switch_active ? " · kill-switch ON" : ""}
                  </p>
                  {cloakPolicy.blocked_reasons.length > 0 && (
                    <p className="text-xs text-amber-800 mb-3" data-testid="cloakbrowser-blocked-reasons">
                      blocked: {cloakPolicy.blocked_reasons.join(", ")}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 items-end">
                    <Input
                      data-testid="cloakbrowser-rationale"
                      value={cloakRationale}
                      onChange={(e) => setCloakRationale(e.target.value)}
                      placeholder="Purpose rationale"
                      className="max-w-md text-sm"
                    />
                    <Button
                      type="button"
                      data-testid="cloakbrowser-request"
                      variant="ghost"
                      className="text-xs border border-slate-200"
                      onClick={() =>
                        void requestCloakBrowser(cloakSourceId, {
                          purpose_rationale: cloakRationale || "Governed partner access",
                          pinned_version: "1.0.0",
                        }).then(setCloakPolicy)
                      }
                    >
                      Request
                    </Button>
                    <Button
                      type="button"
                      data-testid="cloakbrowser-approve-owner"
                      variant="ghost"
                      className="text-xs border border-slate-200"
                      onClick={() => void approveOwnerAdmin(cloakSourceId).then(setCloakPolicy)}
                    >
                      Owner/Admin approve
                    </Button>
                    <Button
                      type="button"
                      data-testid="cloakbrowser-approve-compliance"
                      variant="ghost"
                      className="text-xs border border-slate-200"
                      onClick={() => void approveCompliance(cloakSourceId).then(setCloakPolicy)}
                    >
                      Compliance approve
                    </Button>
                    <Button
                      type="button"
                      data-testid="cloakbrowser-revoke"
                      variant="ghost"
                      className="text-xs border border-slate-200"
                      onClick={() =>
                        void revokeCloakBrowser(cloakSourceId, "admin revoke").then(setCloakPolicy)
                      }
                    >
                      Revoke
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-xs text-slate-500">Loading policy…</p>
              )}
            </div>
          )}
        </AppSection>
        </div>
      </div>

      {/* Auto-Disable Rules and Recovery Panel */}
      <div className="mt-6">
        <AppSection
          title="Connector auto-disable policy"
          description="Per-source auto-disable rules and event history. Recovery is human-confirmed; evaluation cycles consume the US-046 health surface and the US-041 alert metrics."
        >
          {autoSourceId ? (
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-4 gap-4">
                <div className="flex items-center gap-2">
                  <Power className="size-4.5 text-blue-600 animate-pulse" />
                  <h3 className="text-sm font-semibold text-slate-800">
                    Managing policies for: <span className="font-mono text-blue-700 bg-blue-50/80 px-2 py-0.5 rounded-sm border border-blue-100">{selectedConnector?.name || autoSourceId}</span>
                  </h3>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="text-xs h-8 flex items-center gap-1.5 border border-slate-200"
                    data-testid="auto-disable-evaluate-source"
                    onClick={handleComputeEvaluation}
                  >
                    <Activity className="size-3.5 text-slate-500" />
                    Compute Evaluation
                  </Button>
                </div>
              </div>

              {autoMessage && (
                <div className="flex items-start gap-2 p-3.5 bg-slate-50 border border-slate-200 rounded-sm text-xs text-slate-700 font-mono" data-testid="auto-disable-message">
                  <Info className="size-4 text-slate-400 shrink-0 mt-0.5" />
                  <span>{autoMessage}</span>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left side: Rules configuration and form (col-span-5) */}
                <div className="lg:col-span-5 space-y-6">
                  <div className="border border-slate-200 rounded-sm p-4 bg-slate-50/30 space-y-4">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-slate-500 border-b border-slate-100 pb-2">
                      Create Rule
                    </h4>
                    <div className="space-y-3.5 text-xs">
                      <div>
                        <Label className="text-slate-600 font-medium">Trigger Type</Label>
                        <select
                          data-testid="auto-disable-trigger-select"
                          value={ruleTrigger}
                          onChange={(e) => setRuleTrigger(e.target.value as AutoDisableTriggerValue)}
                          className="mt-1 w-full text-xs rounded-sm border border-slate-200 bg-white px-3 py-2 text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          {triggersList.map((t) => (
                            <option key={t.value} value={t.value}>
                              {t.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-slate-600 font-medium">Threshold Value</Label>
                          <Input
                            data-testid="auto-disable-threshold"
                            value={ruleThreshold}
                            onChange={(e) => setRuleThreshold(e.target.value)}
                            placeholder="e.g. 0.2"
                            className="mt-1 text-xs"
                          />
                        </div>
                        <div>
                          <Label className="text-slate-600 font-medium">Consecutive Breaches</Label>
                          <Input
                            data-testid="auto-disable-consecutive"
                            value={ruleConsecutive}
                            onChange={(e) => setRuleConsecutive(e.target.value)}
                            placeholder="3"
                            className="mt-1 text-xs"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Label className="text-slate-600 font-medium">Evaluation Window (s)</Label>
                          <Input
                            data-testid="auto-disable-window"
                            value={ruleWindow}
                            onChange={(e) => setRuleWindow(e.target.value)}
                            placeholder="1800"
                            className="mt-1 text-xs"
                          />
                        </div>
                        <div>
                          <Label className="text-slate-600 font-medium">Cooldown Period (s)</Label>
                          <Input
                            data-testid="auto-disable-cooldown"
                            value={ruleCooldown}
                            onChange={(e) => setRuleCooldown(e.target.value)}
                            placeholder="900"
                            className="mt-1 text-xs"
                          />
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-1">
                        <input
                          type="checkbox"
                          id="ruleEnabled"
                          checked={ruleEnabled}
                          onChange={(e) => setRuleEnabled(e.target.checked)}
                          className="size-3.5 text-blue-600 border-slate-300 rounded-sm"
                        />
                        <Label htmlFor="ruleEnabled" className="text-slate-600 font-medium cursor-pointer">Rule is Enabled</Label>
                      </div>

                      <Button
                        type="button"
                        data-testid="auto-disable-create-rule"
                        onClick={handleCreateRule}
                        className="w-full text-xs h-9 font-semibold mt-2"
                      >
                        <Plus className="size-3.5 mr-1" />
                        Add Policy Rule
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Right side: Rules List and Events Log (col-span-7) */}
                <div className="lg:col-span-7 space-y-6">
                  {/* Rules list */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-slate-500">
                      Configured Rules ({autoRules.length})
                    </h4>
                    <div className="space-y-3">
                      {autoRules.length === 0 ? (
                        <p className="text-xs text-slate-400 py-6 text-center bg-slate-50/50 border border-slate-100 rounded-sm" data-testid="auto-disable-rules-empty">
                          No active auto-disable rules configured for this connector.
                        </p>
                      ) : (
                        autoRules.map((rule) => {
                          const isEnabled = rule.enabled;
                          const getTriggerConfig = (trigger: string) => {
                            switch (trigger) {
                              case "health_unhealthy":
                                return { label: "Unhealthy Health Status", color: "bg-red-50 text-red-700 border-red-200" };
                              case "captcha_rate_breach":
                                return { label: "CAPTCHA Rate Breach", color: "bg-amber-50 text-amber-700 border-amber-200" };
                              case "failure_rate_breach":
                                return { label: "Failure Rate Breach", color: "bg-orange-50 text-orange-700 border-orange-200" };
                              case "needs_user_action_storm":
                                return { label: "User Action Storm", color: "bg-yellow-50 text-yellow-800 border-yellow-200" };
                              case "error_spike":
                                return { label: "Error Rate Spike", color: "bg-rose-50 text-rose-700 border-rose-200" };
                              case "manual_kill_switch":
                                return { label: "Manual Kill Switch", color: "bg-slate-100 text-slate-800 border-slate-300" };
                              default:
                                return { label: trigger, color: "bg-slate-50 text-slate-700 border-slate-200" };
                            }
                          };

                          const triggerConfig = getTriggerConfig(rule.trigger);

                          return (
                            <div
                              key={rule.id}
                              className="group relative flex flex-col gap-3.5 border border-slate-200 bg-white hover:bg-slate-50/40 hover:border-slate-300 hover:shadow-xs transition-all duration-200 rounded-sm p-4"
                              data-testid="auto-disable-rule-row"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2.5">
                                  <span className={`inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-semibold font-mono border ${triggerConfig.color}`}>
                                    {triggerConfig.label}
                                  </span>
                                  <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-50 text-slate-600 border border-slate-100">
                                    <span className={`size-1.5 rounded-full ${isEnabled ? "bg-emerald-500 animate-pulse" : "bg-slate-300"}`} />
                                    {isEnabled ? "Active" : "Disabled"}
                                  </span>
                                </div>
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="ghost"
                                  className="h-7 w-7 p-0 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-sm transition-colors"
                                  data-testid="auto-disable-rule-delete"
                                  onClick={() =>
                                    void deleteAutoDisableRule(rule.id).then(() => void refreshAutoDisable())
                                  }
                                >
                                  <Trash2 className="size-4" />
                                </Button>
                              </div>

                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                                <div className="flex flex-col gap-1 p-2 bg-slate-50/50 border border-slate-100 rounded-sm">
                                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Threshold</span>
                                  <span className="font-semibold text-slate-700 font-mono">{rule.threshold_value}</span>
                                </div>
                                <div className="flex flex-col gap-1 p-2 bg-slate-50/50 border border-slate-100 rounded-sm">
                                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Window</span>
                                  <span className="font-semibold text-slate-700 font-mono">{rule.window_seconds}s</span>
                                </div>
                                <div className="flex flex-col gap-1 p-2 bg-slate-50/50 border border-slate-100 rounded-sm">
                                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Consecutive</span>
                                  <span className="font-semibold text-slate-800 font-mono">{rule.consecutive_breaches}</span>
                                </div>
                                <div className="flex flex-col gap-1 p-2 bg-slate-50/50 border border-slate-100 rounded-sm">
                                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400">Cooldown</span>
                                  <span className="font-semibold text-slate-700 font-mono">{rule.cooldown_seconds}s</span>
                                </div>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  </div>

                  {/* Events log */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-slate-500">
                      Event Log ({autoEvents.length})
                    </h4>
                    <div className="space-y-4">
                      {autoEvents.length === 0 ? (
                        <p className="text-xs text-slate-400 py-6 text-center bg-slate-50/50 border border-slate-100 rounded-sm">
                          No events recorded for this connector.
                        </p>
                      ) : (
                        autoEvents.map((evt) => (
                          <div
                            key={evt.id}
                            className="flex flex-col gap-3 border border-slate-200 bg-white p-4 rounded-sm"
                            data-testid="auto-disable-event-row"
                          >
                            <div className="flex items-center justify-between gap-3 flex-wrap border-b border-slate-100 pb-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-xs font-semibold text-slate-800 font-mono bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-sm">
                                  {evt.trigger}
                                </span>
                                {getEventStatusBadge(evt.status)}
                              </div>
                              {evt.created_at && (
                                <span className="text-[10px] text-slate-400 font-mono">
                                  {new Date(evt.created_at).toLocaleString()}
                                </span>
                              )}
                            </div>

                            <p className="text-xs text-slate-600 bg-slate-50 p-2.5 border border-slate-100 rounded-sm">
                              <span className="font-medium text-slate-500">Reason:</span> {evt.reason}
                            </p>

                            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] text-slate-500 font-mono pt-1">
                              <div>Breaches count: <span className="font-semibold text-slate-700">{evt.breach_count}</span></div>
                              {evt.recovered_at && (
                                <div>Recovered at: <span className="text-slate-700">{new Date(evt.recovered_at).toLocaleDateString()}</span></div>
                              )}
                              {evt.recovery_reason && (
                                <div className="col-span-2">
                                  Recovery reason: <span className="text-slate-600 font-sans italic">"{evt.recovery_reason}"</span>
                                </div>
                              )}
                            </div>

                            {evt.status === "active" && (
                              <div className="border-t border-slate-100 pt-3 mt-1 flex flex-col sm:flex-row gap-2 items-end">
                                <div className="w-full">
                                  <Label className="text-[10px] font-semibold text-slate-600">Recovery Reason</Label>
                                  <Input
                                    placeholder="Provide audit reason for manual recovery"
                                    value={autoRecoveryReason}
                                    onChange={(e) => setAutoRecoveryReason(e.target.value)}
                                    className="mt-1 text-xs h-8"
                                    data-testid="auto-disable-recover-reason"
                                  />
                                </div>
                                <Button
                                  type="button"
                                  size="sm"
                                  className="text-xs shrink-0 h-8 flex items-center gap-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold"
                                  data-testid="auto-disable-recover"
                                  onClick={() => handleRecoverEvent(evt.id)}
                                >
                                  <RefreshCcw className="size-3.5" />
                                  Recover
                                </Button>
                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 bg-slate-50/40 border border-dashed border-slate-200 rounded-sm">
              <ShieldAlert className="size-8 text-slate-300 mb-2.5 animate-pulse" strokeWidth={1.5} />
              <p className="text-xs font-semibold text-slate-600">No connector selected</p>
              <p className="text-[11px] text-slate-400 mt-1 max-w-sm text-center">
                Select a connector from the registered registry table above to manage its auto-disable policy rules, event history, and recover status.
              </p>
            </div>
          )}
        </AppSection>
      </div>
      </div>
    </AppPageShell>
  );
}