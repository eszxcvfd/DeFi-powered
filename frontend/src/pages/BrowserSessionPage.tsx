import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  cancelBrowserAction,
  confirmBrowserAction,
  runBrowserAction,
  type BrowserActionResult,
} from "@/api/browserActions";
import {
  captureBrowserScreenshot,
  fetchArtifactObjectUrl,
  listBrowserArtifacts,
  setBrowserDebug,
  type BrowserArtifactView,
} from "@/api/browserArtifacts";
import {
  createBrowserSessionForEvent,
  createBrowserSessionForSource,
  getBrowserSession,
  stopBrowserSession,
  type BrowserSessionView,
} from "@/api/browserSessions";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { Button } from "@/components/ui/button";
import {
  Camera,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  FileText,
  Link2,
  Loader2,
  MousePointerClick,
  ScrollText,
  Play,
  Square,
  X,
} from "lucide-react";

function stateLabel(state: string) {
  return state.replace(/_/g, " ");
}

type ActivityItem = {
  id: string;
  at: number;
  label: string;
  lifecycle: string;
  summary: string;
  detail?: string | null;
  textPreview?: string | null;
  url?: string | null;
};

function lifecycleTone(lifecycle: string) {
  if (lifecycle === "failed" || lifecycle === "timeout" || lifecycle === "blocked") return "text-red-700 bg-red-50 border-red-100";
  if (lifecycle === "needs_user_action") return "text-amber-900 bg-amber-50 border-amber-100";
  if (lifecycle === "confirmation_required") return "text-amber-900 bg-amber-50 border-amber-100";
  return "text-emerald-900 bg-emerald-50 border-emerald-100";
}

export default function BrowserSessionPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const sessionId = params.get("session");
  const [session, setSession] = useState<BrowserSessionView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [pendingConfirmation, setPendingConfirmation] = useState<BrowserActionResult | null>(null);
  const [artifacts, setArtifacts] = useState<BrowserArtifactView[]>([]);
  const [debugBusy, setDebugBusy] = useState(false);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [expandedTextId, setExpandedTextId] = useState<string | null>(null);
  const [lastReadText, setLastReadText] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewArtifactId, setPreviewArtifactId] = useState<string | null>(null);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [artifactPage, setArtifactPage] = useState(1);

  const pushActivity = useCallback((item: Omit<ActivityItem, "id" | "at">) => {
    setActivity((prev) => [
      { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, at: Date.now(), ...item },
      ...prev.slice(0, 14),
    ]);
  }, []);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      setSession(await getBrowserSession(sessionId));
      try {
        setArtifacts(await listBrowserArtifacts(sessionId));
      } catch {
        setArtifacts([]);
      }
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    setActivity([]);
    setPendingConfirmation(null);
    setLastReadText(null);
    setExpandedTextId(null);
    refresh();
    const t = setInterval(() => {
      if (!session?.terminal) refresh();
    }, 1500);
    return () => clearInterval(t);
  }, [sessionId, session?.terminal, refresh]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const loadScreenshotPreview = async (artifactId: string) => {
    if (!sessionId) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    try {
      const url = await fetchArtifactObjectUrl(sessionId, artifactId);
      setPreviewUrl(url);
      setPreviewArtifactId(artifactId);
    } catch (e) {
      setError(String(e));
    }
  };

  const onStop = async () => {
    if (!sessionId) return;
    setStopping(true);
    try {
      setSession(await stopBrowserSession(sessionId));
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setStopping(false);
    }
  };

  const runAction = async (
    label: string,
    actionType: string,
    parameters: Record<string, unknown> = {},
  ) => {
    if (!sessionId) return;
    setActionBusy(true);
    try {
      const r = await runBrowserAction(sessionId, actionType, parameters);
      let summary = r.summary;
      if (actionType === "scroll" && r.lifecycle === "completed") {
        summary = `${r.summary} — take a screenshot to see the new viewport.`;
      }
      if (actionType === "open_detail" && r.lifecycle === "timeout") {
        summary = `${r.summary} Try “Read page text” or open the page in your browser.`;
      }
      pushActivity({
        label,
        lifecycle: r.lifecycle,
        summary,
        detail: r.detail,
        textPreview: r.text_preview ?? null,
        url: r.current_url ?? null,
      });
      if (r.lifecycle === "confirmation_required" && r.confirmation_id) {
        setPendingConfirmation(r);
      } else if (actionType !== "submit_form") {
        setPendingConfirmation(null);
      }
      await refresh();
      if (actionType === "read_text" && r.text_preview) {
        setLastReadText(r.text_preview);
        setExpandedTextId("latest");
      }
    } catch (e) {
      pushActivity({
        label,
        lifecycle: "failed",
        summary: String(e),
      });
      setError(String(e));
    } finally {
      setActionBusy(false);
    }
  };

  if (!sessionId) {
    return (
      <AppPageShell testId="browser-session-console">
        <AppPageHeader title="Browser session" subtitle="Supervised Playwright worker for event sources." />
        <div className={PAGE_CONTENT_CLASS}>
          <p className="text-sm text-slate-600">
            Open a session from an{" "}
            <Link to="/events" className="underline font-medium">
              event
            </Link>{" "}
            → <span className="font-mono text-xs">Open browser session</span>.
          </p>
        </div>
      </AppPageShell>
    );
  }

  if (error && !session) {
    return <p className="p-8 text-red-600">{error}</p>;
  }

  if (!session) {
    return (
      <div className="p-10 flex justify-center" data-testid="browser-session-loading">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  const actionable = session.state === "running" || session.state === "needs_user_action";
  const screenshots = artifacts.filter((a) => a.artifact_type === "screenshot" && a.status === "active");
  const displayReadText = lastReadText ?? activity.find((a) => a.textPreview)?.textPreview ?? null;

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-slate-50/80" data-testid="browser-session-console">
      <div className="border-b border-slate-200 bg-white sticky top-0 z-20 px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-4 min-w-0">
          <Link to="/events" className="text-xs text-slate-500 shrink-0 hover:text-slate-800">
            ← Events
          </Link>
          <div className="min-w-0">
            <h1 className="text-base font-bold text-slate-900 truncate">Supervised browser session</h1>
            <p className="text-[10px] text-slate-400 font-mono truncate max-w-md" data-testid="browser-session-id">
              {session.id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={`text-xs font-medium capitalize px-2.5 py-1 rounded-full border ${
              session.state === "running"
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : session.state === "needs_user_action"
                  ? "bg-amber-50 text-amber-900 border-amber-200"
                  : "bg-slate-100 text-slate-700 border-slate-200"
            }`}
            data-testid="browser-session-state"
          >
            {stateLabel(session.state)}
          </span>
          <span className="text-xs text-slate-500 font-mono" data-testid="browser-session-runtime">
            {session.runtime_seconds}s · {session.engine}
          </span>
          {!session.terminal && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={stopping || session.state === "stopping"}
              onClick={onStop}
              data-testid="browser-session-stop"
            >
              {stopping ? <Loader2 className="size-4 animate-spin mr-1" /> : <Square className="size-4 mr-1" />}
              Stop
            </Button>
          )}
        </div>
      </div>

      <div className="px-4 sm:px-6 lg:px-8 py-6 max-w-[1600px] mx-auto">
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* Left: live page context + preview */}
          <div className="xl:col-span-5 space-y-4">
            <section className="border border-slate-200 rounded-lg bg-white overflow-hidden shadow-sm">
              <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/80">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600">Page in session</h2>
                <p className="text-[11px] text-slate-500 mt-1">
                  Supervised worker URL — many sites block live embed; use screenshot or open in a new tab.
                </p>
              </div>
              <div className="p-4 space-y-3">
                <p className="text-xs font-mono break-all text-slate-700" data-testid="browser-session-url">
                  {session.current_url || session.target?.initial_url || "—"}
                </p>
                {(session.current_url || session.target?.initial_url) && (
                  <a
                    href={session.current_url || session.target?.initial_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-sky-700 hover:underline"
                    data-testid="browser-session-open-external"
                  >
                    <ExternalLink className="size-3.5" />
                    Open current page in your browser
                  </a>
                )}
                <div
                  className="relative aspect-[4/3] max-h-[420px] w-full rounded-md border border-dashed border-slate-200 bg-slate-100 flex items-center justify-center overflow-hidden"
                  data-testid="browser-page-preview"
                >
                  {previewUrl ? (
                    <button
                      type="button"
                      className="w-full h-full block cursor-zoom-in"
                      onClick={() => setLightboxOpen(true)}
                      data-testid="browser-screenshot-preview"
                    >
                      <img src={previewUrl} alt="Session screenshot" className="w-full h-full object-contain" />
                    </button>
                  ) : (
                    <div className="text-center px-6 text-slate-400 text-xs">
                      <Camera className="size-8 mx-auto mb-2 opacity-40" />
                      Take a screenshot to preview the supervised page here.
                    </div>
                  )}
                </div>
                {screenshots.length > 0 && (
                  <div className="flex gap-2 flex-wrap" data-testid="browser-screenshot-thumbs">
                    {screenshots.slice(0, 6).map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        className={`text-[10px] px-2 py-1 rounded border ${
                          previewArtifactId === a.id
                            ? "border-slate-800 bg-slate-900 text-white"
                            : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"
                        }`}
                        onClick={() => loadScreenshotPreview(a.id)}
                      >
                        {new Date(a.created_at ?? "").toLocaleTimeString() || "shot"}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="border border-slate-200 rounded-lg bg-white p-4 text-xs text-slate-600 space-y-2">
              <p>
                <span className="text-slate-400 uppercase tracking-wide text-[10px]">Latest action</span>
                <br />
                <span data-testid="browser-session-latest-action">{session.latest_action_summary}</span>
              </p>
              <p className="font-mono text-[10px] text-slate-400 break-all">{session.isolation.profile_boundary}</p>
            </section>
          </div>

          {/* Right: controls */}
          <div className="xl:col-span-7 space-y-4">
            {actionable && (
              <section
                className="border border-slate-200 rounded-lg bg-white p-4 shadow-sm"
                data-testid="browser-read-only-actions"
              >
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Read-only actions</h2>
                <p className="text-[11px] text-slate-500 mb-4">
                  Scroll moves the worker viewport. Read text extracts visible copy. Open first link clicks the first
                  semantic link (may time out on heavy or protected pages).
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="justify-start h-auto py-2.5 border border-slate-200"
                    disabled={actionBusy}
                    data-testid="browser-action-scroll"
                    onClick={() => runAction("Scroll down", "scroll", { delta_y: 400 })}
                  >
                    <ScrollText className="size-4 mr-2 shrink-0 text-slate-500" />
                    <span className="text-left">
                      <span className="block font-medium text-xs">Scroll down</span>
                      <span className="block text-[10px] text-slate-500 font-normal">+400px in worker</span>
                    </span>
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="justify-start h-auto py-2.5 border border-slate-200"
                    disabled={actionBusy}
                    data-testid="browser-action-read-text"
                    onClick={() => runAction("Read page text", "read_text", { max_chars: 8000 })}
                  >
                    <FileText className="size-4 mr-2 shrink-0 text-slate-500" />
                    <span className="text-left">
                      <span className="block font-medium text-xs">Read page text</span>
                      <span className="block text-[10px] text-slate-500 font-normal">Up to 8k chars</span>
                    </span>
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    className="justify-start h-auto py-2.5 border border-slate-200"
                    disabled={actionBusy}
                    data-testid="browser-action-open-detail"
                    onClick={() => runAction("Open first link", "open_detail", {})}
                  >
                    <Link2 className="size-4 mr-2 shrink-0 text-slate-500" />
                    <span className="text-left">
                      <span className="block font-medium text-xs">Open first link</span>
                      <span className="block text-[10px] text-slate-500 font-normal">First &lt;link&gt; on page</span>
                    </span>
                  </Button>
                </div>

                {displayReadText && (
                  <div className="mt-4 border border-slate-200 rounded-md overflow-hidden" data-testid="browser-text-preview-panel">
                    <button
                      type="button"
                      className="w-full flex items-center justify-between px-3 py-2 bg-slate-50 text-xs font-medium text-slate-700"
                      onClick={() => setExpandedTextId(expandedTextId ? null : "latest")}
                    >
                      Extracted page text
                      {expandedTextId ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                    </button>
                    {expandedTextId && displayReadText && (
                      <textarea
                        readOnly
                        className="w-full min-h-[200px] max-h-[360px] text-xs font-mono p-3 border-0 resize-y bg-white text-slate-800"
                        value={displayReadText}
                        data-testid="browser-action-text-full"
                      />
                    )}
                  </div>
                )}
              </section>
            )}

            {actionable && (
              <section
                className="border border-slate-200 rounded-lg bg-white p-4 shadow-sm"
                data-testid="browser-debug-artifacts"
              >
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Debug artifacts</h2>
                <p className="text-[11px] text-slate-500 mb-3" data-testid="browser-debug-enabled-state">
                  Debug: {session.debug_enabled ? "on" : "off"}
                  {session.latest_artifact_summary ? ` — ${session.latest_artifact_summary}` : ""}
                </p>
                <div className="flex flex-wrap gap-2 mb-3">
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={debugBusy}
                    data-testid="browser-debug-enable"
                    onClick={async () => {
                      if (!sessionId) return;
                      setDebugBusy(true);
                      try {
                        await setBrowserDebug(sessionId, !session.debug_enabled);
                        await refresh();
                      } catch (e) {
                        setError(String(e));
                      } finally {
                        setDebugBusy(false);
                      }
                    }}
                  >
                    {session.debug_enabled ? "Disable debug" : "Enable debug"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    disabled={debugBusy}
                    data-testid="browser-artifact-screenshot"
                    onClick={async () => {
                      if (!sessionId) return;
                      setDebugBusy(true);
                      try {
                        const shot = await captureBrowserScreenshot(sessionId);
                        await refresh();
                        if (shot.id) await loadScreenshotPreview(shot.id);
                        pushActivity({
                          label: "Screenshot",
                          lifecycle: shot.status,
                          summary: shot.summary || "Screenshot captured",
                        });
                      } catch (e) {
                        setError(String(e));
                      } finally {
                        setDebugBusy(false);
                      }
                    }}
                  >
                    <Camera className="size-4 mr-1" />
                    Take screenshot
                  </Button>
                </div>
                <ul className="text-xs space-y-1.5" data-testid="browser-artifact-list">
                  {artifacts.length === 0 ? (
                    <li className="text-slate-400">No artifacts yet.</li>
                  ) : (
                    paginateSlice(artifacts, artifactPage).map((a) => (
                      <li key={a.id} className="flex items-center justify-between gap-2 font-mono text-slate-600">
                        <span>
                          {a.artifact_type} · {a.status}
                        </span>
                        {a.artifact_type === "screenshot" && a.status === "active" && (
                          <button
                            type="button"
                            className="text-sky-700 hover:underline text-[10px] font-sans"
                            onClick={() => loadScreenshotPreview(a.id)}
                          >
                            View
                          </button>
                        )}
                      </li>
                    ))
                  )}
                </ul>
                <ListPagination
                  page={artifactPage}
                  totalItems={artifacts.length}
                  onPageChange={setArtifactPage}
                  testId="browser-artifact-pagination"
                />
              </section>
            )}

            {actionable && (
              <section
                className="border border-amber-200/80 rounded-lg bg-amber-50/30 p-4"
                data-testid="browser-confirmation-gated-actions"
              >
                <h2 className="text-xs font-bold uppercase tracking-wider text-amber-950 mb-1">
                  Confirmation-gated actions
                </h2>
                <p className="text-[11px] text-amber-900/80 mb-3">
                  Preview side effects before any submit-like action runs in the worker.
                </p>
                {!pendingConfirmation ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={actionBusy}
                    data-testid="browser-action-request-submit"
                    onClick={() =>
                      runAction("Submit preview", "submit_form", {
                        form_id: "primary",
                        target_label: "Primary form",
                      })
                    }
                  >
                    <MousePointerClick className="size-4 mr-1" />
                    Request submit (preview)
                  </Button>
                ) : (
                  <div className="border border-amber-200 rounded-md bg-white p-3" data-testid="browser-confirmation-preview">
                    <p className="text-sm font-medium text-amber-950">
                      {pendingConfirmation.preview?.title ?? "Side-effect preview"}
                    </p>
                    <p className="text-xs text-amber-900 mt-2">{pendingConfirmation.preview?.impact_summary}</p>
                    <p className="text-xs text-slate-600 mt-2 font-mono" data-testid="browser-confirmation-state">
                      {pendingConfirmation.confirmation_state ?? "pending"}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      <Button
                        type="button"
                        size="sm"
                        disabled={actionBusy}
                        data-testid="browser-confirmation-confirm"
                        onClick={async () => {
                          if (!sessionId || !pendingConfirmation.confirmation_id) return;
                          setActionBusy(true);
                          try {
                            const r = await confirmBrowserAction(
                              sessionId,
                              pendingConfirmation.confirmation_id,
                            );
                            setPendingConfirmation(null);
                            pushActivity({
                              label: "Confirm submit",
                              lifecycle: r.lifecycle,
                              summary: r.summary,
                            });
                            await refresh();
                          } catch (e) {
                            setError(String(e));
                          } finally {
                            setActionBusy(false);
                          }
                        }}
                      >
                        Confirm
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        disabled={actionBusy}
                        data-testid="browser-confirmation-cancel"
                        onClick={async () => {
                          if (!sessionId || !pendingConfirmation.confirmation_id) return;
                          setActionBusy(true);
                          try {
                            const r = await cancelBrowserAction(
                              sessionId,
                              pendingConfirmation.confirmation_id,
                            );
                            setPendingConfirmation(null);
                            pushActivity({ label: "Cancel submit", lifecycle: r.lifecycle, summary: r.summary });
                            await refresh();
                          } catch (e) {
                            setError(String(e));
                          } finally {
                            setActionBusy(false);
                          }
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </section>
            )}

            <section className="border border-slate-200 rounded-lg bg-white p-4 shadow-sm">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">Activity log</h2>
              {activity.length === 0 ? (
                <p className="text-xs text-slate-400">Run an action to see results here.</p>
              ) : (
                <ul className="space-y-2 max-h-[280px] overflow-y-auto" data-testid="browser-action-result">
                  {activity.map((item) => (
                    <li
                      key={item.id}
                      className={`text-xs border rounded-md p-2.5 ${lifecycleTone(item.lifecycle)}`}
                    >
                      <div className="flex justify-between gap-2">
                        <span className="font-semibold">{item.label}</span>
                        <span className="font-mono text-[10px] opacity-80">{item.lifecycle}</span>
                      </div>
                      <p className="mt-1">{item.summary}</p>
                      {item.detail && (
                        <p className="mt-1 opacity-90 break-words" data-testid="browser-action-detail">
                          {item.detail}
                        </p>
                      )}
                      {item.url && item.lifecycle === "completed" && (
                        <p className="mt-1 font-mono text-[10px] break-all">URL: {item.url}</p>
                      )}
                      {item.textPreview && (
                        <p className="mt-1 line-clamp-3 font-mono text-[10px] opacity-90">{item.textPreview}</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>

        {session.state === "needs_user_action" && (
          <p className="mt-6 text-sm text-amber-800 border border-amber-200 bg-amber-50 rounded-lg p-4" data-testid="browser-session-needs-user">
            The worker could not fully load this page (auth, bot check, or HTTP error). Open the link above in your
            normal browser, or try Read page text / screenshot on what loaded.
          </p>
        )}
        {session.terminal && (
          <section
            className="mt-6 border border-slate-200 rounded-lg bg-white p-5 shadow-sm"
            data-testid="browser-session-ended-panel"
          >
            <p className="text-sm text-slate-800 font-medium" data-testid="browser-session-stopped">
              Session ended ({stateLabel(session.state)}).
            </p>
            <p className="text-xs text-slate-600 mt-2 max-w-2xl">
              A stopped session cannot be resumed — the browser worker was closed on purpose. Start a{" "}
              <strong>new</strong> supervised session (new ID) with the same event or URL below.
            </p>
            <div className="flex flex-wrap gap-2 mt-4">
              {session.target.event_id && session.target.source_id && (
                <Button
                  type="button"
                  size="sm"
                  disabled={restarting}
                  data-testid="browser-session-start-new"
                  onClick={async () => {
                    setRestarting(true);
                    setError(null);
                    try {
                      const sess = await createBrowserSessionForEvent(
                        session.target.event_id!,
                        session.target.source_id,
                      );
                      navigate(`/browser?session=${sess.id}`, { replace: true });
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setRestarting(false);
                    }
                  }}
                >
                  {restarting ? <Loader2 className="size-4 animate-spin mr-1" /> : <Play className="size-4 mr-1" />}
                  Start new session (same event)
                </Button>
              )}
              {session.target.source_id && session.target.initial_url && !session.target.event_id && (
                <Button
                  type="button"
                  size="sm"
                  disabled={restarting}
                  data-testid="browser-session-start-new"
                  onClick={async () => {
                    setRestarting(true);
                    setError(null);
                    try {
                      const sess = await createBrowserSessionForSource(
                        session.target.source_id,
                        session.target.initial_url,
                      );
                      navigate(`/browser?session=${sess.id}`, { replace: true });
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setRestarting(false);
                    }
                  }}
                >
                  {restarting ? <Loader2 className="size-4 animate-spin mr-1" /> : <Play className="size-4 mr-1" />}
                  Start new session (same URL)
                </Button>
              )}
              {session.target.event_id && (
                <Link
                  to={`/events/${session.target.event_id}`}
                  className="inline-flex h-8 items-center rounded-sm px-3 text-xs font-medium hover:bg-slate-100"
                  data-testid="browser-session-back-event"
                >
                  Back to event
                </Link>
              )}
              <Link
                to="/events"
                className="inline-flex h-8 items-center rounded-sm px-3 text-xs font-medium hover:bg-slate-100"
              >
                Browse events
              </Link>
            </div>
          </section>
        )}
        {error && (
          <p className="mt-4 text-sm text-red-600 bg-red-50 border border-red-100 rounded-md p-3">{error}</p>
        )}
      </div>

      {lightboxOpen && previewUrl && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          role="dialog"
          aria-modal
          data-testid="browser-screenshot-lightbox"
        >
          <button
            type="button"
            className="absolute top-4 right-4 text-white/90 hover:text-white p-2"
            onClick={() => setLightboxOpen(false)}
            aria-label="Close"
          >
            <X className="size-6" />
          </button>
          <img src={previewUrl} alt="Screenshot full size" className="max-w-full max-h-[90vh] object-contain rounded" />
        </div>
      )}
    </div>
  );
}