import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getEvent, refreshAudience, rescoreEvent } from "@/api/events";
import { Button } from "@/components/ui/button";
import { PRIORITY_LABELS } from "@/constants/priority";
import { SCORING_LABELS } from "@/constants/scoring";
import type { EventDetail } from "@/types/event";
import { Loader2, RefreshCw } from "lucide-react";

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rescoring, setRescoring] = useState(false);
  const [audienceLoading, setAudienceLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    getEvent(id)
      .then(setEvent)
      .catch((e) => setError(String(e)));
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
    </div>
  );
}