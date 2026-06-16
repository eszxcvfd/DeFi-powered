import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCampaign } from "@/api/campaigns";
import { cancelDiscoveryJob, getDiscoveryJob, startDiscovery } from "@/api/discovery";
import {
  createDiscoverySchedule,
  listDiscoverySchedules,
  patchDiscoverySchedule,
} from "@/api/discoverySchedules";
import { putDiscoveryCopilotFeedback } from "@/api/aiFeedback";
import { acceptDiscoveryCopilot, askDiscoveryCopilot } from "@/api/discoveryCopilot";
import {
  generateQueryExpansion,
  getQueryExpansion,
  patchQueryExpansion,
} from "@/api/queryExpansion";
import {
  approveScoringSuggestion,
  generateScoringSuggestions,
  listScoringSuggestions,
  rejectScoringSuggestion,
} from "@/api/scoringSuggestions";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { SCORING_LABELS } from "@/constants/scoring";
import type { CampaignDetail as CampaignDetailType } from "@/types/campaign";
import type { DiscoveryJob } from "@/types/discovery";
import type { DiscoverySchedule } from "@/types/discoverySchedule";
import { AiFeedbackControls } from "@/components/AiFeedbackControls";
import type { DiscoveryCopilotResponse } from "@/types/discoveryCopilot";
import type { QueryExpansionSet, QueryExpansionVariant } from "@/types/queryExpansion";
import type { ScoringSuggestionSet } from "@/types/scoringSuggestions";
import { Play, X, Loader2, CheckCircle2, AlertCircle, Database, HelpCircle, Activity } from "lucide-react";

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<CampaignDetailType | null>(null);
  const [job, setJob] = useState<DiscoveryJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [schedules, setSchedules] = useState<DiscoverySchedule[]>([]);
  const [scheduleBusy, setScheduleBusy] = useState(false);
  const [expansion, setExpansion] = useState<QueryExpansionSet | null>(null);
  const [expansionBusy, setExpansionBusy] = useState(false);
  const [useExpansion, setUseExpansion] = useState(true);
  const [copilotQuestion, setCopilotQuestion] = useState("");
  const [copilotAnswer, setCopilotAnswer] = useState<DiscoveryCopilotResponse | null>(null);
  const [copilotBusy, setCopilotBusy] = useState(false);
  const [scoringSuggestions, setScoringSuggestions] = useState<ScoringSuggestionSet[]>([]);
  const [scoringSuggestBusy, setScoringSuggestBusy] = useState(false);

  const pollJob = useCallback(async (jobId: string) => {
    const j = await getDiscoveryJob(jobId);
    setJob(j);
    return j;
  }, []);

  useEffect(() => {
    if (!id) return;
    getCampaign(id)
      .then(setCampaign)
      .catch((e) => setError(String(e)));
    listDiscoverySchedules(id)
      .then(setSchedules)
      .catch(() => setSchedules([]));
    getQueryExpansion(id)
      .then(setExpansion)
      .catch(() => setExpansion(null));
    listScoringSuggestions(id)
      .then(setScoringSuggestions)
      .catch(() => setScoringSuggestions([]));
  }, [id]);

  useEffect(() => {
    if (!job?.id) return;
    const terminal = ["succeeded", "failed", "partial", "cancelled", "needs_user_action"];
    if (terminal.includes(job.status)) return;
    const t = setInterval(() => {
      void pollJob(job.id);
    }, 500);
    return () => clearInterval(t);
  }, [job?.id, job?.status, pollJob]);

  async function runDiscovery() {
    if (!id) return;
    setRunning(true);
    setError(null);
    try {
      const created = await startDiscovery(id, { use_expansion: useExpansion });
      setJob(created);
      for (let i = 0; i < 40; i++) {
        const j = await pollJob(created.id);
        if (["succeeded", "failed", "partial", "cancelled", "needs_user_action"].includes(j.status)) break;
        await new Promise((r) => setTimeout(r, 300));
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  async function cancelJob() {
    if (!job) return;
    setJob(await cancelDiscoveryJob(job.id));
  }

  function flattenVariants(set: QueryExpansionSet): QueryExpansionVariant[] {
    return Object.values(set.grouped_variants).flat();
  }

  async function runGenerateExpansion() {
    if (!id) return;
    setExpansionBusy(true);
    try {
      setExpansion(await generateQueryExpansion(id));
    } catch (e) {
      setError(String(e));
    } finally {
      setExpansionBusy(false);
    }
  }

  async function askCopilot() {
    if (!id || !copilotQuestion.trim()) return;
    setCopilotBusy(true);
    try {
      setCopilotAnswer(await askDiscoveryCopilot(id, copilotQuestion.trim()));
    } catch (e) {
      setError(String(e));
    } finally {
      setCopilotBusy(false);
    }
  }

  async function acceptCopilotIntoExpansion() {
    if (!id || !copilotAnswer) return;
    setCopilotBusy(true);
    try {
      await acceptDiscoveryCopilot(id, copilotAnswer.id);
      setExpansion(await getQueryExpansion(id));
      setCopilotAnswer({ ...copilotAnswer, accepted_at: new Date().toISOString() });
    } catch (e) {
      setError(String(e));
    } finally {
      setCopilotBusy(false);
    }
  }

  async function approveExpansion() {
    if (!id || !expansion) return;
    setExpansionBusy(true);
    try {
      const updated = await patchQueryExpansion(id, {
        variants: flattenVariants(expansion),
        approve: true,
      });
      setExpansion(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setExpansionBusy(false);
    }
  }

  const pendingScoringSuggestion = scoringSuggestions.find((s) => s.status === "pending_review");

  async function runGenerateScoringSuggestion() {
    if (!id) return;
    setScoringSuggestBusy(true);
    try {
      const created = await generateScoringSuggestions(id);
      setScoringSuggestions((prev) => [created, ...prev.filter((p) => p.id !== created.id)]);
    } catch (e) {
      setError(String(e));
    } finally {
      setScoringSuggestBusy(false);
    }
  }

  async function approveScoringSuggestionSet() {
    if (!id || !pendingScoringSuggestion) return;
    setScoringSuggestBusy(true);
    try {
      const res = await approveScoringSuggestion(id, pendingScoringSuggestion.id);
      setScoringSuggestions((prev) =>
        prev.map((s) => (s.id === res.suggestion.id ? res.suggestion : s))
      );
      setCampaign((c) => (c ? { ...c, scoring_weights: res.campaign.scoring_weights } : c));
    } catch (e) {
      setError(String(e));
    } finally {
      setScoringSuggestBusy(false);
    }
  }

  async function rejectScoringSuggestionSet() {
    if (!id || !pendingScoringSuggestion) return;
    setScoringSuggestBusy(true);
    try {
      const rejected = await rejectScoringSuggestion(id, pendingScoringSuggestion.id);
      setScoringSuggestions((prev) =>
        prev.map((s) => (s.id === rejected.id ? rejected : s))
      );
    } catch (e) {
      setError(String(e));
    } finally {
      setScoringSuggestBusy(false);
    }
  }

  async function createSchedule() {
    if (!id) return;
    setScheduleBusy(true);
    try {
      const created = await createDiscoverySchedule(id, {
        recurrence: { kind: "daily", timezone: "UTC", hour: 9, minute: 0 },
      });
      setSchedules((prev) => [created, ...prev]);
    } catch (e) {
      setError(String(e));
    } finally {
      setScheduleBusy(false);
    }
  }

  async function toggleSchedulePause(sched: DiscoverySchedule) {
    setScheduleBusy(true);
    try {
      const next = sched.enabled_state === "paused" ? "enabled" : "paused";
      const updated = await patchDiscoverySchedule(sched.id, { enabled_state: next });
      setSchedules((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e) {
      setError(String(e));
    } finally {
      setScheduleBusy(false);
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "succeeded":
        return <CheckCircle2 className="size-4 text-emerald-600" />;
      case "failed":
        return <AlertCircle className="size-4 text-red-600" />;
      case "running":
        return <Loader2 className="size-4 animate-spin text-blue-600" />;
      default:
        return <Activity className="size-4 text-slate-400" />;
    }
  };

  if (error && !campaign) {
    return (
      <AppPageShell>
        <p className="p-8 text-red-600">{error}</p>
      </AppPageShell>
    );
  }
  if (!campaign) {
    return (
      <AppPageShell>
        <div className="p-10 flex items-center justify-center">
          <Loader2 className="size-5 animate-spin text-slate-400" />
        </div>
      </AppPageShell>
    );
  }

  return (
    <AppPageShell testId="campaign-detail">
      <AppPageHeader
        backTo="/campaigns"
        backLabel="Campaigns"
        title={campaign.name}
        subtitle={campaign.description}
        meta={
          <Link
            to={`/campaigns/${campaign.id}/events`}
            className="text-xs font-medium text-sky-700 hover:underline"
            data-testid="campaign-view-events"
          >
            View event results →
          </Link>
        }
        actions={
          <>
            <Button
              type="button"
              size="sm"
              data-testid="run-discovery"
              disabled={running}
              onClick={() => void runDiscovery()}
              className="gap-2"
            >
              {running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" fill="currentColor" />}
              {running ? "Running…" : "Run discovery"}
            </Button>
            {job && !["succeeded", "failed", "partial", "cancelled", "needs_user_action"].includes(job.status) && (
              <Button
                type="button"
                size="sm"
                variant="ghost"
                data-testid="cancel-discovery"
                onClick={() => void cancelJob()}
                className="border border-slate-200 gap-1.5"
              >
                <X className="size-3.5" />
                Cancel job
              </Button>
            )}
          </>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        <p className="sr-only" data-testid="campaign-detail-name">
          {campaign.name}
        </p>
        {error && (
          <p className="mb-4 text-sm text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg">{error}</p>
        )}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="xl:col-span-8">
            <AppSection title="Discovery copilot" testId="discovery-copilot-panel" className="mb-6">
              <p className="text-sm text-slate-500 mb-3">
                Ask a bounded discovery question; answers stay structured and reviewable. Requires{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">LIVELEAD_GOOGLE_AI_STUDIO_API_KEY</code>{" "}
                in repo-root <code className="text-xs bg-slate-100 px-1 rounded">.env</code> with{" "}
                <code className="text-xs bg-slate-100 px-1 rounded">LIVELEAD_DISCOVERY_COPILOT_PROVIDER=gemini</code>.
              </p>
              <textarea
                className="w-full min-h-[72px] text-sm border border-slate-200 rounded-lg p-3"
                data-testid="discovery-copilot-question"
                placeholder="What livestream topics should we prioritize for this campaign?"
                value={copilotQuestion}
                onChange={(e) => setCopilotQuestion(e.target.value)}
              />
              <div className="flex gap-2 mt-2">
                <Button
                  type="button"
                  size="sm"
                  data-testid="discovery-copilot-ask"
                  disabled={copilotBusy || copilotQuestion.trim().length < 8}
                  onClick={() => void askCopilot()}
                >
                  Ask copilot
                </Button>
              </div>
              {copilotAnswer && (
                <div className="mt-4 space-y-3 text-sm border border-slate-100 rounded-lg p-4" data-testid="discovery-copilot-answer">
                  <p data-testid="discovery-copilot-confidence">
                    Confidence: {(copilotAnswer.structured.confidence * 100).toFixed(0)}%
                  </p>
                  <div>
                    <p className="text-[11px] font-mono uppercase text-slate-400">Claims</p>
                    <ul className="list-disc pl-5">
                      {copilotAnswer.structured.claims.map((c) => (
                        <li key={c.text}>{c.text}</li>
                      ))}
                    </ul>
                  </div>
                  {copilotAnswer.structured.risk_flags.length > 0 && (
                    <div data-testid="discovery-copilot-risks">
                      <p className="text-[11px] font-mono uppercase text-amber-600">Risk flags</p>
                      <ul className="text-amber-800 text-xs space-y-1">
                        {copilotAnswer.structured.risk_flags.map((r) => (
                          <li key={r.code}>{r.message}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <AiFeedbackControls
                    mode="copilot"
                    current={copilotAnswer.viewer_feedback}
                    busy={copilotBusy}
                    onSubmit={async (payload) => {
                      if (!copilotAnswer) return;
                      setCopilotBusy(true);
                      try {
                        const fb = await putDiscoveryCopilotFeedback(copilotAnswer.id, payload);
                        setCopilotAnswer({ ...copilotAnswer, viewer_feedback: fb });
                      } catch (e) {
                        setError(String(e));
                      } finally {
                        setCopilotBusy(false);
                      }
                    }}
                  />
                  {!copilotAnswer.accepted_at && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      className="border border-slate-200"
                      data-testid="discovery-copilot-accept"
                      disabled={copilotBusy}
                      onClick={() => void acceptCopilotIntoExpansion()}
                    >
                      Send framing to query expansion
                    </Button>
                  )}
                </div>
              )}
            </AppSection>
            <AppSection title="Query expansion" testId="query-expansion-panel" className="mb-6">
              <p className="text-sm text-slate-500 mb-3">
                Generate reviewable keyword variants before discovery runs.
              </p>
              <div className="flex flex-wrap items-center gap-3 mb-4">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="border border-slate-200"
                  data-testid="query-expansion-generate"
                  disabled={expansionBusy}
                  onClick={() => void runGenerateExpansion()}
                >
                  Generate suggestions
                </Button>
                {expansion && (
                  <span className="text-xs font-mono text-slate-500" data-testid="query-expansion-status">
                    {expansion.status}
                    {expansion.requires_review ? " · review required" : ""}
                  </span>
                )}
                <label className="flex items-center gap-2 text-sm text-slate-600 ml-auto">
                  <input
                    type="checkbox"
                    checked={useExpansion}
                    onChange={(e) => setUseExpansion(e.target.checked)}
                    data-testid="query-expansion-use-toggle"
                  />
                  Use approved expansion on run
                </label>
              </div>
              {expansion && Object.keys(expansion.grouped_variants).length > 0 ? (
                <div className="space-y-3 text-sm" data-testid="query-expansion-variants">
                  {Object.entries(expansion.grouped_variants).map(([kind, items]) => (
                    <div key={kind}>
                      <p className="text-[11px] font-mono uppercase text-slate-400 tracking-wider">{kind}</p>
                      <ul className="mt-1 flex flex-wrap gap-2">
                        {items.map((v) => (
                          <li
                            key={`${kind}-${v.text}`}
                            className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-xs"
                          >
                            {v.text}
                            {v.source === "ai" ? " (AI)" : ""}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                  {expansion.status !== "approved" && (
                    <Button
                      type="button"
                      size="sm"
                      data-testid="query-expansion-approve"
                      disabled={expansionBusy}
                      onClick={() => void approveExpansion()}
                    >
                      Approve set
                    </Button>
                  )}
                </div>
              ) : (
                <p className="text-sm text-slate-400">No expansion set yet.</p>
              )}
            </AppSection>
            <AppSection title="Discovery engine" testId="discovery-run">
              {!job ? (
                <div className="py-8 text-center text-slate-400">
                  <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                  <p className="text-sm">No discovery run yet. Use Run discovery in the header.</p>
                </div>
              ) : (
                <div className="space-y-4" data-testid="discovery-progress">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-500">Pipeline state</span>
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-mono border uppercase ${
                        job.status === "succeeded"
                          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                          : job.status === "failed"
                            ? "bg-red-50 text-red-700 border-red-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                      }`}
                      data-testid="discovery-status"
                    >
                      {getStatusIcon(job.status)}
                      {job.status}
                    </span>
                  </div>
                  {job.progress.sources && (
                    <div className="space-y-2">
                      <p className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Source crawl</p>
                      <div className="border border-slate-100 rounded-md divide-y divide-slate-100">
                        {Object.entries(job.progress.sources).map(([sid, s]) => (
                          <div key={sid} className="flex items-center justify-between p-3 text-sm">
                            <span className="font-mono text-slate-800">{sid.slice(0, 8)}…</span>
                            <div className="flex items-center gap-3 text-xs">
                              <span className="text-slate-500">
                                {s.items_found != null ? `${s.items_found} items` : ""}
                              </span>
                              <span className="inline-flex items-center gap-1 font-mono">
                                {getStatusIcon(s.status)}
                                {s.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </AppSection>
            <AppSection title="Scheduled discovery" testId="discovery-schedule-panel" className="mt-6">
              <div className="flex items-center justify-between gap-3 mb-4">
                <p className="text-sm text-slate-500">Bounded daily recurrence with next-run preview.</p>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="border border-slate-200"
                  data-testid="discovery-schedule-create"
                  disabled={scheduleBusy}
                  onClick={() => void createSchedule()}
                >
                  Add daily schedule
                </Button>
              </div>
              <div data-testid="discovery-schedule-list" className="space-y-3">
                {schedules.length === 0 ? (
                  <p className="text-sm text-slate-400">No schedules yet.</p>
                ) : (
                  schedules.map((s) => (
                    <div
                      key={s.id}
                      className="border border-slate-100 rounded-lg p-3 text-sm space-y-2"
                      data-testid="discovery-schedule-row"
                    >
                      <div className="flex justify-between items-center gap-2">
                        <span className="font-medium text-slate-800">{s.recurrence_summary}</span>
                        <span
                          className="text-xs font-mono uppercase text-slate-500"
                          data-testid="discovery-schedule-state"
                        >
                          {s.enabled_state}
                        </span>
                      </div>
                      {s.next_run_at && (
                        <p className="text-xs text-slate-500" data-testid="discovery-schedule-next-run">
                          Next run: {new Date(s.next_run_at).toLocaleString()}
                        </p>
                      )}
                      {s.latest_job && (
                        <p className="text-xs text-slate-500">
                          Latest job: {s.latest_job.status}
                        </p>
                      )}
                      <div className="flex gap-2">
                        {s.enabled_state === "paused" ? (
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            data-testid="discovery-schedule-resume"
                            disabled={scheduleBusy}
                            onClick={() => void toggleSchedulePause(s)}
                          >
                            Resume
                          </Button>
                        ) : (
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            data-testid="discovery-schedule-pause"
                            disabled={scheduleBusy}
                            onClick={() => void toggleSchedulePause(s)}
                          >
                            Pause
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </AppSection>
          </div>
          <div className="xl:col-span-4">
            <AppSection title="Scoring weights" testId="campaign-scoring-weights">
              <div
                className="mb-4 rounded-md border border-slate-200 bg-slate-50/80 p-3 space-y-3"
                data-testid="scoring-suggestion-panel"
              >
                <p className="text-xs text-slate-600">
                  Feedback-derived weight suggestions are advisory until you approve them.
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="border border-slate-200"
                    data-testid="scoring-suggestion-generate"
                    disabled={scoringSuggestBusy}
                    onClick={() => void runGenerateScoringSuggestion()}
                  >
                    Generate from feedback
                  </Button>
                  {pendingScoringSuggestion && (
                    <span
                      className="text-xs font-mono text-slate-500"
                      data-testid="scoring-suggestion-status"
                    >
                      pending review · confidence {(pendingScoringSuggestion.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                {pendingScoringSuggestion ? (
                  <div className="space-y-2 text-sm" data-testid="scoring-suggestion-review">
                    <p className="text-slate-700">{pendingScoringSuggestion.summary}</p>
                    {pendingScoringSuggestion.deltas.length > 0 ? (
                      <ul className="space-y-1 text-xs text-slate-600">
                        {pendingScoringSuggestion.deltas.map((d) => (
                          <li key={d.component}>
                            {SCORING_LABELS[d.component] ?? d.component}:{" "}
                            {(d.current_weight * 100).toFixed(0)}% →{" "}
                            {(d.proposed_weight * 100).toFixed(0)}% — {d.rationale}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500">No weight deltas in this set.</p>
                    )}
                    <div className="flex gap-2 pt-1">
                      <Button
                        type="button"
                        size="sm"
                        data-testid="scoring-suggestion-approve"
                        disabled={scoringSuggestBusy || !pendingScoringSuggestion.deltas.length}
                        onClick={() => void approveScoringSuggestionSet()}
                      >
                        Approve weights
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        data-testid="scoring-suggestion-reject"
                        disabled={scoringSuggestBusy}
                        onClick={() => void rejectScoringSuggestionSet()}
                      >
                        Reject
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400" data-testid="scoring-suggestion-empty">
                    No pending suggestion. Generate after audience or copilot feedback accumulates.
                  </p>
                )}
              </div>
              <div className="space-y-4">
                {Object.entries(campaign.scoring_weights).map(([k, v]) => (
                  <div key={k} className="space-y-1.5">
                    <div className="flex justify-between text-sm font-medium text-slate-700">
                      <span>{SCORING_LABELS[k] ?? k}</span>
                      <span className="font-mono">{(v * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2 rounded-sm overflow-hidden">
                      <div
                        className="bg-slate-800 h-full rounded-sm"
                        style={{ width: `${Math.max(0, Math.min(100, v * 100))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-500 flex gap-2">
                <HelpCircle className="size-4 shrink-0" />
                Weights drive automatic event priority in the pipeline.
              </p>
            </AppSection>
          </div>
        </div>
      </div>
    </AppPageShell>
  );
}