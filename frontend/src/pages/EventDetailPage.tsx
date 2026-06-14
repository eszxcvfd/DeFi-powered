import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createBrowserSessionForEvent } from "@/api/browserSessions";
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
import { Button } from "@/components/ui/button";
import { PRIORITY_LABELS } from "@/constants/priority";
import { SCORING_LABELS } from "@/constants/scoring";
import type { EventDetail } from "@/types/event";
import { Loader2, RefreshCw } from "lucide-react";

export default function EventDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rescoring, setRescoring] = useState(false);
  const [audienceLoading, setAudienceLoading] = useState(false);
  const [engagementLoading, setEngagementLoading] = useState(false);
  const [taskUpdating, setTaskUpdating] = useState<string | null>(null);
  const [leadCreating, setLeadCreating] = useState(false);
  const [leadMessage, setLeadMessage] = useState<string | null>(null);
  const [browserLaunching, setBrowserLaunching] = useState(false);
  const [browserLaunchError, setBrowserLaunchError] = useState<string | null>(null);
  const [browserSources, setBrowserSources] = useState<BrowserLaunchSourceOption[]>([]);
  const [selectedBrowserSourceId, setSelectedBrowserSourceId] = useState("");

  useEffect(() => {
    if (!id) return;
    getEvent(id)
      .then(setEvent)
      .catch((e) => setError(String(e)));
    listEventBrowserLaunchSources(id)
      .then((opts) => {
        setBrowserSources(opts);
        const first = opts.find((o) => o.runnable) ?? opts[0];
        if (first) setSelectedBrowserSourceId(first.source_id);
      })
      .catch(() => setBrowserSources([]));
  }, [id]);

  if (error && !event) return <p className="p-8 text-red-600">{error}</p>;
  if (!event) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-4xl mx-auto" data-testid="event-detail">
      <Link to={`/campaigns/${event.campaign_id}/events`} className="text-xs text-[var(--color-muted)]">
        ← Events
      </Link>
      <h1 className="text-xl font-bold mt-4">{event.canonical_title}</h1>
      <p className="text-sm text-slate-600 mt-2">{event.description}</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-sm text-slate-600">
        <div>
          <dt className="text-xs uppercase text-slate-400">Organizer</dt>
          <dd>{event.organizer || "—"}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase text-slate-400">Region</dt>
          <dd>{event.region || "—"}</dd>
        </div>
      </dl>

      <section className="mt-8 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-provenance-panel">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Provenance & confidence</h2>
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
          <div className="text-xs text-violet-800 bg-violet-50 border border-violet-100 p-2 rounded-sm mb-4">
            <p className="font-semibold">Merge notes</p>
            {event.provenance.merge_notes.map((n, i) => (
              <p key={i}>{n.note}</p>
            ))}
          </div>
        )}
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-source-evidence">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Source evidence</h2>
        <ul className="divide-y divide-slate-100">
          {event.observations.map((o) => (
            <li key={o.id} className="py-3 text-sm">
              <p className="font-medium">{o.raw_title}</p>
              <p className="text-xs text-slate-500 font-mono truncate">{o.source_url}</p>
              <p className="text-xs text-slate-400 mt-1">source {o.source_id.slice(0, 8)}… · {o.observed_at}</p>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-4 border-t border-slate-100" data-testid="event-browser-launch-panel">
          <p className="text-xs text-slate-500 mb-2">
            Playwright connector is created automatically from source evidence URLs (no Admin step).
          </p>
          {browserSources.length > 0 ? (
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="text-xs border border-slate-200 rounded-sm px-2 py-1.5 max-w-xs"
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
              Preparing Playwright connector from evidence… reload the page if this persists.
            </p>
          )}
          {browserLaunchError && (
            <p className="text-xs text-red-600 mt-2" data-testid="event-browser-launch-error">
              {browserLaunchError}
            </p>
          )}
        </div>
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-audience-panel">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Audience hypotheses</h2>
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
        </div>
        {event.audience.state === "empty" ? (
          <p className="text-sm text-slate-500" data-testid="audience-empty">
            {event.audience.generation_notes[0] ?? "Not enough context for audience segments."}
          </p>
        ) : event.audience.hypotheses.length === 0 ? (
          <p className="text-sm text-amber-700">Audience analysis pending.</p>
        ) : (
          <ul className="space-y-4">
            {event.audience.hypotheses.map((h) => (
              <li key={h.id} className="border border-slate-100 p-3 rounded-sm" data-testid="audience-hypothesis">
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
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-engagement-panel">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Engagement plan (US-008)</h2>
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
        </div>
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
                      <li key={t.id} className="border border-slate-100 p-3 rounded-sm text-sm" data-testid="engagement-task">
                        <div className="flex justify-between gap-2">
                          <span className="font-medium">{t.title}</span>
                          <select
                            className="text-xs border border-slate-200 rounded px-1 py-0.5"
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
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-content-summary">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Generated drafts (US-009)</h2>
          {id && (
            <Link to={`/events/${id}/content`} className="text-xs font-medium text-slate-700 underline" data-testid="open-content-studio">
              Open content studio
            </Link>
          )}
        </div>
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
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-score-panel">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Score (US-006)</h2>
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
        </div>
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
      </section>

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="event-leads-panel">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-4">Leads</h2>
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
      </section>
    </div>
  );
}