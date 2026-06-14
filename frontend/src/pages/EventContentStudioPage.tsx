import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  approveContent,
  exportContentUrl,
  fetchContentContext,
  generateContent,
  listContentDrafts,
  markContentUsed,
  patchContentDraft,
  recordContentCopy,
  rejectContent,
  submitForReview,
  type ContentDraft,
} from "@/api/content";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export default function EventContentStudioPage() {
  const { id } = useParams<{ id: string }>();
  const [context, setContext] = useState<Awaited<ReturnType<typeof fetchContentContext>> | null>(null);
  const [drafts, setDrafts] = useState<ContentDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [contentType, setContentType] = useState("outreach");
  const [platform, setPlatform] = useState("email");
  const [tone, setTone] = useState("professional");
  const [cta, setCta] = useState("Learn more");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [rejectNote, setRejectNote] = useState("");
  const [rejectingId, setRejectingId] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([fetchContentContext(id), listContentDrafts(id).catch(() => [])])
      .then(([ctx, d]) => {
        setContext(ctx);
        setDrafts(d);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="content-studio">
      <Link to={`/events/${id}`} className="text-xs text-[var(--color-muted)]">
        ← Event detail
      </Link>
      <h1 className="text-xl font-bold mt-4">Content studio (US-009 / US-010 / US-011)</h1>
      <p className="text-sm text-slate-500 mt-1">Human-controlled handoff — copy/export does not send messages.</p>
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}

      {context && (
        <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="content-context-panel">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-3">Generation context</h2>
          <dl className="grid grid-cols-2 gap-2 text-sm text-slate-600">
            <div>
              <dt className="text-xs text-slate-400">Event</dt>
              <dd>{context.event_title}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Campaign focus</dt>
              <dd>{context.campaign_focus}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Score</dt>
              <dd>{context.score_summary}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Audience</dt>
              <dd>{context.audience_summary}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Plan tasks</dt>
              <dd>{context.plan_task_count}</dd>
            </div>
          </dl>
        </section>
      )}

      <section className="mt-6 border border-slate-200 p-5 rounded-sm bg-white" data-testid="content-settings">
        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-3">Settings</h2>
        <div className="flex flex-wrap gap-3 text-sm">
          <label className="flex flex-col gap-1">
            Type
            <select
              className="border border-slate-200 rounded px-2 py-1"
              value={contentType}
              onChange={(e) => setContentType(e.target.value)}
              data-testid="content-type"
            >
              <option value="outreach">Outreach</option>
              <option value="follow_up">Follow up</option>
              <option value="event_intro">Event intro</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Platform
            <select
              className="border border-slate-200 rounded px-2 py-1"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              data-testid="content-platform"
            >
              <option value="email">Email</option>
              <option value="linkedin">LinkedIn</option>
              <option value="slack">Slack</option>
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Tone
            <input className="border border-slate-200 rounded px-2 py-1" value={tone} onChange={(e) => setTone(e.target.value)} />
          </label>
          <label className="flex flex-col gap-1">
            CTA
            <input className="border border-slate-200 rounded px-2 py-1" value={cta} onChange={(e) => setCta(e.target.value)} />
          </label>
        </div>
        <Button
          type="button"
          className="mt-4"
          size="sm"
          data-testid="content-generate"
          disabled={generating || !id}
          onClick={async () => {
            if (!id) return;
            setGenerating(true);
            try {
              const res = await generateContent({
                event_id: id,
                settings: {
                  content_type: contentType,
                  platform,
                  language: "en",
                  tone,
                  length: "medium",
                  cta,
                  variant_count: 2,
                },
              });
              setContext(res.context);
              setDrafts(res.drafts);
            } catch (e) {
              setError(String(e));
            } finally {
              setGenerating(false);
            }
          }}
        >
          {generating ? <Loader2 className="size-4 animate-spin" /> : "Generate variants"}
        </Button>
      </section>

      <section className="mt-6 space-y-4" data-testid="content-variants">
        {drafts.length === 0 ? (
          <p className="text-sm text-slate-500" data-testid="content-empty">
            No drafts yet.
          </p>
        ) : (
          drafts.map((d) => (
            <article key={d.id} className="border border-slate-200 p-5 rounded-sm bg-white" data-testid="content-draft">
              <div className="flex justify-between text-xs text-slate-500 mb-2">
                <span>
                  Variant {d.variant_index + 1} · {d.settings.platform} · {d.provider}
                </span>
                <span className="font-mono uppercase" data-testid="content-review-status">
                  {d.review_status}
                  {d.ready_for_use ? " · ready" : ""}
                  {d.usage_status === "used" ? " · used" : ""}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 mb-3 text-xs">
                {d.review_status === "draft" || d.review_status === "rejected" ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    data-testid="content-submit-review"
                    onClick={async () => {
                      if (!id) return;
                      try {
                        const u = await submitForReview(id, d.id);
                        setDrafts((p) => p.map((x) => (x.id === d.id ? u : x)));
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Submit for review
                  </Button>
                ) : null}
                {d.review_status === "in_review" ? (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      data-testid="content-approve"
                      onClick={async () => {
                        if (!id) return;
                        try {
                          const u = await approveContent(id, d.id);
                          setDrafts((p) => p.map((x) => (x.id === d.id ? u : x)));
                        } catch (e) {
                          setError(String(e));
                        }
                      }}
                    >
                      Approve
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      data-testid="content-reject"
                      onClick={() => setRejectingId(d.id)}
                    >
                      Reject
                    </Button>
                  </>
                ) : null}
                {d.handoff_available ? (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      data-testid="content-copy"
                      onClick={async () => {
                        if (!id) return;
                        try {
                          await navigator.clipboard.writeText(d.body_text);
                          const u = await recordContentCopy(id, d.id);
                          setDrafts((p) => p.map((x) => (x.id === d.id ? u : x)));
                        } catch (e) {
                          setError(String(e));
                        }
                      }}
                    >
                      Copy
                    </Button>
                    <a
                      className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 border border-slate-200"
                      data-testid="content-export-md"
                      href={exportContentUrl(id!, d.id, "markdown")}
                      download
                    >
                      Export MD
                    </a>
                    {d.usage_status !== "used" ? (
                      <Button
                        type="button"
                        size="sm"
                        data-testid="content-mark-used"
                        onClick={async () => {
                          if (!id) return;
                          try {
                            const u = await markContentUsed(id, d.id);
                            setDrafts((p) => p.map((x) => (x.id === d.id ? u : x)));
                          } catch (e) {
                            setError(String(e));
                          }
                        }}
                      >
                        Mark used
                      </Button>
                    ) : null}
                  </>
                ) : null}
              </div>
              {d.handoff_history && d.handoff_history.length > 0 && (
                <ul className="text-xs text-slate-500 mb-2" data-testid="content-handoff-history">
                  {d.handoff_history.slice(0, 3).map((h) => (
                    <li key={h.id}>
                      {h.action} by {h.actor}
                      {h.export_format ? ` (${h.export_format})` : ""}
                    </li>
                  ))}
                </ul>
              )}
              {rejectingId === d.id && (
                <div className="mb-3 flex gap-2 items-end">
                  <input
                    className="flex-1 border border-slate-200 rounded px-2 py-1 text-sm"
                    placeholder="Rejection note"
                    value={rejectNote}
                    onChange={(e) => setRejectNote(e.target.value)}
                    data-testid="content-reject-note"
                  />
                  <Button
                    size="sm"
                    onClick={async () => {
                      if (!id) return;
                      try {
                        const u = await rejectContent(id, d.id, rejectNote);
                        setDrafts((p) => p.map((x) => (x.id === d.id ? u : x)));
                        setRejectingId(null);
                        setRejectNote("");
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Confirm reject
                  </Button>
                </div>
              )}
              {d.review_history && d.review_history.length > 0 && (
                <ul className="text-xs text-slate-500 mb-2" data-testid="content-review-history">
                  {d.review_history.slice(0, 3).map((h) => (
                    <li key={h.id}>
                      {h.action}: {h.from_status} → {h.to_status} by {h.actor}
                      {h.note ? ` — ${h.note}` : ""}
                    </li>
                  ))}
                </ul>
              )}
              {d.risk_flags.length > 0 && (
                <ul className="mb-3 text-xs text-amber-800 bg-amber-50 border border-amber-100 p-2 rounded-sm" data-testid="content-risk-flags">
                  {d.risk_flags.map((f, i) => (
                    <li key={i}>
                      <strong>{f.code}</strong>: {f.message}
                    </li>
                  ))}
                </ul>
              )}
              {editingId === d.id ? (
                <div className="space-y-2">
                  <textarea
                    className="w-full min-h-32 border border-slate-200 rounded p-2 text-sm font-mono"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    data-testid="content-draft-editor"
                  />
                  <Button
                    size="sm"
                    data-testid="content-save-draft"
                    onClick={async () => {
                      if (!id) return;
                      try {
                        const updated = await patchContentDraft(id, d.id, editText);
                        setDrafts((prev) => prev.map((x) => (x.id === d.id ? updated : x)));
                        setEditingId(null);
                      } catch (e) {
                        setError(String(e));
                      }
                    }}
                  >
                    Save edit
                  </Button>
                </div>
              ) : (
                <>
                  <pre className="text-sm whitespace-pre-wrap text-slate-700 font-sans">{d.body_text}</pre>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="mt-2"
                    data-testid="content-edit-draft"
                    onClick={() => {
                      setEditingId(d.id);
                      setEditText(d.body_text);
                    }}
                  >
                    Edit draft
                  </Button>
                </>
              )}
            </article>
          ))
        )}
      </section>
    </div>
  );
}