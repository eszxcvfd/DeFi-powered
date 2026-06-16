import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createBrowserSessionForEvent } from "@/api/browserSessions";
import { putAudienceHypothesisFeedback } from "@/api/aiFeedback";
import {
  createEngagementPlan,
  getEvent,
  listEventBrowserLaunchSources,
  patchEngagementTask,
  refreshAudience,
  rescoreEvent,
  type BrowserLaunchSourceOption,
} from "@/api/events";
import { createLead } from "@/api/leads";
import EventHistoryPanel from "@/components/EventHistoryPanel";
import EventOverridePanel from "@/components/EventOverridePanel";
import EventWatchPanel from "@/components/EventWatchPanel";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { AiFeedbackControls } from "@/components/AiFeedbackControls";
import { Button } from "@/components/ui/button";
import { PRIORITY_LABELS } from "@/constants/priority";
import { SCORING_LABELS } from "@/constants/scoring";
import type { EventDetail, EventFieldProvenance, EventWatchState } from "@/types/event";
import { Loader2, RefreshCw } from "lucide-react";

export default function EventDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rescoring, setRescoring] = useState(false);
  const [audienceLoading, setAudienceLoading] = useState(false);
  const [audienceFeedbackBusy, setAudienceFeedbackBusy] = useState(false);
  const [engagementLoading, setEngagementLoading] = useState(false);
  const [taskUpdating, setTaskUpdating] = useState<string | null>(null);
  const [leadCreating, setLeadCreating] = useState(false);
  const [leadMessage, setLeadMessage] = useState<string | null>(null);
  const [browserLaunching, setBrowserLaunching] = useState(false);
  const [browserLaunchError, setBrowserLaunchError] = useState<string | null>(null);
  const [browserSources, setBrowserSources] = useState<BrowserLaunchSourceOption[]>([]);
  const [selectedBrowserSourceId, setSelectedBrowserSourceId] = useState("");
  const [observationPage, setObservationPage] = useState(1);
  const [watch, setWatch] = useState<EventWatchState | null>(null);
  const [overrides, setOverrides] = useState<EventFieldProvenance[]>([]);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  useEffect(() => {
    if (!id) return;
    getEvent(id)
      .then((ev) => {
        setEvent(ev);
        setWatch(ev.watch);
        setOverrides(ev.overrides ?? []);
      })
      .catch((e) => setError(String(e)));
    listEventBrowserLaunchSources(id)
      .then((opts) => {
        setBrowserSources(opts);
        const first = opts.find((o) => o.runnable) ?? opts[0];
        if (first) setSelectedBrowserSourceId(first.source_id);
      })
      .catch(() => setBrowserSources([]));
  }, [id]);

  if (error && !event) {
    return (
      <AppPageShell>
        <p className="p-8 text-red-600">{error}</p>
      </AppPageShell>
    );
  }
  if (!event) {
    return (
      <AppPageShell>
        <div className="p-10 flex justify-center">
          <Loader2 className="size-5 animate-spin" />
        </div>
      </AppPageShell>
    );
  }

  return (
    <AppPageShell testId="event-detail">
      <AppPageHeader
        backTo={`/campaigns/${event.campaign_id}/events`}
        backLabel="Events"
        title={event.canonical_title}
        subtitle={event.description || undefined}
        meta={
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-[11px] text-slate-500">
            <div>
              <span className="uppercase text-slate-400 mr-1">Organizer</span>
              {event.organizer || "—"}
            </div>
            <div>
              <span className="uppercase text-slate-400 mr-1">Region</span>
              {event.region || "—"}
            </div>
          </dl>
        }
        actions={
          id ? (
            <Link
              to={`/events/${id}/content`}
              className="text-xs font-medium text-slate-700 underline"
              data-testid="open-content-studio"
            >
              Content studio
            </Link>
          ) : null
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        {watch ? (
          <AppSection
            title="Watchlist"
            description="Track this event and optionally schedule a reminder."
            testId="event-watch-section"
            className="mb-6"
          >
            <EventWatchPanel eventId={event.id} watch={watch} onChanged={setWatch} />
          </AppSection>
        ) : null}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          <div className="xl:col-span-5 space-y-4">
            <AppSection
              title="Manual overrides"
              description="Override canonical fields and protect them from later normalization."
              testId="event-overrides-panel"
            >
              <EventOverridePanel
                eventId={event.id}
                provenance={overrides}
                onChanged={(next) => {
                  setOverrides(next);
                  setHistoryRefreshKey((k) => k + 1);
                }}
              />
            </AppSection>
            <AppSection
              title="Change history"
              description="Append-only timeline of edits, clear actions, and protected-field skips."
              testId="event-history-panel"
            >
              <EventHistoryPanel
                eventId={event.id}
                refreshKey={historyRefreshKey}
              />
            </AppSection>
            <AppSection title="Provenance & confidence" testId="event-provenance-panel">
              <p className="text-sm mb-3">
                Summary:{" "}
                <span className="font-mono" data-testid="event-confidence-summary">
                  {event.provenance.confidence_summary}
                </span>
                {" · "}
                {event.provenance.observation_count} observation(s)
              </p>
              <ul className="text-xs text-slate-600 space-y-1 mb-4">
                {event.provenance.field_confidence.map((f) => (
                  <li key={f.field}>
                    <span className="font-mono">{f.field}</span> — {f.trust}: {f.note}
                  </li>
                ))}
              </ul>
              {event.provenance.merge_notes.length > 0 && (
                <div className="text-xs text-violet-800 bg-violet-50 border border-violet-100 p-2 rounded-md">
                  <p className="font-semibold">Merge notes</p>
                  {event.provenance.merge_notes.map((n, i) => (
                    <p key={i}>{n.note}</p>
                  ))}
                </div>
              )}
            </AppSection>

            <AppSection
              title="Source evidence"
              description="Browser session can use Playwright or Selenium connectors provisioned from these URLs."
              testId="event-source-evidence"
            >
              <ul className="divide-y divide-slate-100">
                {paginateSlice(event.observations, observationPage).map((o) => (
                  <li key={o.id} className="py-3 text-sm first:pt-0">
                    <p className="font-medium">{o.raw_title}</p>
                    <p className="text-xs text-slate-500 font-mono break-all">{o.source_url}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      source {o.source_id.slice(0, 8)}… · {o.observed_at}
                    </p>
                  </li>
                ))}
              </ul>
              <ListPagination
                page={observationPage}
                totalItems={event.observations.length}
                onPageChange={setObservationPage}
                testId="event-observations-pagination"
              />
              <div className="mt-4 pt-4 border-t border-slate-100" data-testid="event-browser-launch-panel">
                {browserSources.length > 0 ? (
                  <div className="flex flex-wrap items-center gap-2">
                    <select
                      className="text-xs border border-slate-200 rounded-md px-2 py-1.5 max-w-xs bg-white"
                      data-testid="event-browser-source-select"
                      value={selectedBrowserSourceId}
                      onChange={(e) => setSelectedBrowserSourceId(e.target.value)}
                    >
                      {browserSources.map((o) => (
                        <option key={o.source_id} value={o.source_id} disabled={!o.runnable}>
                          {o.name} ({o.engine})
                          {!o.runnable ? " — blocked" : ""}
                        </option>
                      ))}
                    </select>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      data-testid="event-open-browser-session"
                      disabled={
                        browserLaunching ||
                        !selectedBrowserSourceId ||
                        !browserSources.find((o) => o.source_id === selectedBrowserSourceId)?.runnable
                      }
                      onClick={async () => {
                        if (!id || !selectedBrowserSourceId) return;
                        setBrowserLaunching(true);
                        setBrowserLaunchError(null);
                        try {
                          const sess = await createBrowserSessionForEvent(id, selectedBrowserSourceId);
                          navigate(`/browser?session=${sess.id}`);
                        } catch (e) {
                          setBrowserLaunchError(String(e));
                        } finally {
                          setBrowserLaunching(false);
                        }
                      }}
                    >
                      {browserLaunching ? <Loader2 className="size-3.5 animate-spin mr-2" /> : null}
                      Open browser session
                    </Button>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500" data-testid="event-browser-launch-wait">
                    Preparing browser connectors (Playwright / Selenium) from evidence… reload if this persists.
                  </p>
                )}
                {browserLaunchError && (
                  <p className="text-xs text-red-600 mt-2" data-testid="event-browser-launch-error">
                    {browserLaunchError}
                  </p>
                )}
              </div>
            </AppSection>
          </div>

          <div className="xl:col-span-7 space-y-4">
            <AppSection
              title="Score"
              testId="event-score-panel"
              actions={
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  data-testid="event-rescore"
                  disabled={rescoring}
                  onClick={async () => {
                    if (!id) return;
                    setRescoring(true);
                    try {
                      setEvent(await rescoreEvent(id));
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setRescoring(false);
                    }
                  }}
                  className="gap-1.5"
                >
                  {rescoring ? <Loader2 className="size-3.5 animate-spin" /> : <RefreshCw className="size-3.5" />}
                  Re-score
                </Button>
              }
            >
              {event.score_state === "missing" || !event.score ? (
                <p className="text-sm text-amber-700">No score yet. Re-score to compute.</p>
              ) : (
                <div className="space-y-2 text-sm">
                  <span data-testid="event-total-score">
                    <strong>{event.score.total_score.toFixed(1)}</strong> / 100 —{" "}
                    {PRIORITY_LABELS[event.score.priority_level] ?? event.score.priority_level}
                  </span>
                  <ul>
                    {event.score.components.slice(0, 4).map((c) => (
                      <li key={c.key} className="text-xs text-slate-600">
                        {SCORING_LABELS[c.key] ?? c.key}: +{c.weighted_contribution.toFixed(1)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </AppSection>

            <AppSection
              title="Audience hypotheses"
              testId="event-audience-panel"
              actions={
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  data-testid="audience-refresh"
                  disabled={audienceLoading}
                  onClick={async () => {
                    if (!id) return;
                    setAudienceLoading(true);
                    try {
                      setEvent(await refreshAudience(id));
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setAudienceLoading(false);
                    }
                  }}
                >
                  {audienceLoading ? <Loader2 className="size-3.5 animate-spin" /> : "Refresh"}
                </Button>
              }
            >
              {event.audience.state === "empty" ? (
                <p className="text-sm text-slate-500" data-testid="audience-empty">
                  {event.audience.generation_notes[0] ?? "Not enough context for audience segments."}
                </p>
              ) : event.audience.hypotheses.length === 0 ? (
                <p className="text-sm text-amber-700">Audience analysis pending.</p>
              ) : (
                <ul className="space-y-4">
                  {event.audience.hypotheses.map((h) => (
                    <li key={h.id} className="border border-slate-100 p-3 rounded-md" data-testid="audience-hypothesis">
                      <div className="flex justify-between text-sm font-medium">
                        <span>{h.segment_name}</span>
                        <span className="font-mono text-xs text-slate-500">
                          {h.fit_type} · {(h.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 mt-1">{h.reason}</p>
                      <ul className="mt-2 text-xs text-slate-500 space-y-1">
                        {h.evidence.map((e, i) => (
                          <li key={i}>
                            <span className="font-mono">{e.kind}</span>: {e.detail}
                          </li>
                        ))}
                      </ul>
                      <AiFeedbackControls
                        mode="audience"
                        current={h.viewer_feedback}
                        busy={audienceFeedbackBusy}
                        onSubmit={async (payload) => {
                          if (!id || !event) return;
                          setAudienceFeedbackBusy(true);
                          try {
                            await putAudienceHypothesisFeedback(h.id, payload);
                            setEvent(await getEvent(id));
                          } catch (e) {
                            setError(String(e));
                          } finally {
                            setAudienceFeedbackBusy(false);
                          }
                        }}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </AppSection>

            <AppSection
              title="Engagement plan"
              testId="event-engagement-panel"
              actions={
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  data-testid="engagement-create"
                  disabled={engagementLoading || event.score_state === "missing"}
                  onClick={async () => {
                    if (!id) return;
                    setEngagementLoading(true);
                    try {
                      setEvent(await createEngagementPlan(id));
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setEngagementLoading(false);
                    }
                  }}
                >
                  {engagementLoading ? <Loader2 className="size-3.5 animate-spin" /> : "Create / refresh plan"}
                </Button>
              }
            >
              {event.score_state === "missing" ? (
                <p className="text-sm text-amber-700">Score the event before generating an engagement plan.</p>
              ) : event.engagement.state === "missing" ? (
                <p className="text-sm text-slate-500" data-testid="engagement-empty">
                  {event.engagement.generation_notes[0] ?? "No plan yet. Create one to see phased tasks."}
                </p>
              ) : (
                <div className="space-y-6">
                  {(["PRE_EVENT", "LIVE_EVENT", "POST_EVENT"] as const).map((phase) => {
                    const tasks = event.engagement.tasks.filter((t) => t.phase === phase);
                    if (tasks.length === 0) return null;
                    const label =
                      phase === "PRE_EVENT" ? "Before event" : phase === "LIVE_EVENT" ? "During event" : "After event";
                    return (
                      <div key={phase} data-testid={`engagement-phase-${phase}`}>
                        <h3 className="text-xs font-semibold uppercase text-slate-500 mb-2">{label}</h3>
                        <ul className="space-y-3">
                          {tasks.map((t) => (
                            <li
                              key={t.id}
                              className="border border-slate-100 p-3 rounded-md text-sm"
                              data-testid="engagement-task"
                            >
                              <div className="flex justify-between gap-2">
                                <span className="font-medium">{t.title}</span>
                                <select
                                  className="text-xs border border-slate-200 rounded px-1 py-0.5 bg-white"
                                  data-testid="engagement-task-status"
                                  value={t.status}
                                  disabled={taskUpdating === t.id}
                                  onChange={async (ev) => {
                                    if (!id) return;
                                    setTaskUpdating(t.id);
                                    try {
                                      setEvent(await patchEngagementTask(id, t.id, { status: ev.target.value }));
                                    } catch (e) {
                                      setError(String(e));
                                    } finally {
                                      setTaskUpdating(null);
                                    }
                                  }}
                                >
                                  <option value="TODO">Todo</option>
                                  <option value="IN_PROGRESS">In progress</option>
                                  <option value="DONE">Done</option>
                                  <option value="SKIPPED">Skipped</option>
                                </select>
                              </div>
                              <p className="text-slate-600 mt-1 text-xs">{t.rationale}</p>
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })}
                </div>
              )}
            </AppSection>

            <AppSection title="Generated drafts" testId="event-content-summary">
              {event.generated_content?.length ? (
                <ul className="text-sm text-slate-600 space-y-1">
                  {event.generated_content.map((g) => (
                    <li key={g.id}>
                      Variant {g.variant_index + 1} ({g.platform}) — {g.review_status}
                      {g.ready_for_use ? " ✓ ready" : ""} — {g.risk_flag_count} flag(s)
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-500">No drafts yet.</p>
              )}
            </AppSection>

            <AppSection title="Leads" testId="event-leads-panel">
              {event.leads?.has_linked_lead ? (
                <p className="text-sm text-slate-600">
                  {event.leads.linked_count} linked lead(s).{" "}
                  <Link to="/leads" className="underline">
                    Open pipeline
                  </Link>
                </p>
              ) : (
                <>
                  <p className="text-sm text-slate-600 mb-3">No lead linked to this event yet.</p>
                  <Button
                    type="button"
                    size="sm"
                    data-testid="event-create-lead"
                    disabled={leadCreating}
                    onClick={async () => {
                      if (!event) return;
                      setLeadCreating(true);
                      setLeadMessage(null);
                      try {
                        await createLead({
                          display_name: event.canonical_title.slice(0, 120),
                          company: (event.organizer || "").trim(),
                          title: event.region ? `Event · ${event.region}` : "Event prospect",
                          discovery_source: "event",
                          event_id: event.id,
                          campaign_id: event.campaign_id,
                          public_url: `${event.source_url}#event-${event.id}`,
                          origin_kind: "event",
                        });
                        setEvent(await getEvent(event.id));
                        setLeadMessage("Lead created. View it in the pipeline.");
                      } catch (e) {
                        const msg = String(e);
                        setLeadMessage(msg);
                        if (msg.includes("duplicate")) {
                          setEvent(await getEvent(event.id));
                        }
                      } finally {
                        setLeadCreating(false);
                      }
                    }}
                  >
                    {leadCreating ? "Creating…" : "Create lead from event"}
                  </Button>
                </>
              )}
              {leadMessage && <p className="text-xs mt-2 text-slate-600">{leadMessage}</p>}
            </AppSection>
          </div>
        </div>
        {error && event && (
          <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg p-3">{error}</p>
        )}
      </div>
    </AppPageShell>
  );
}