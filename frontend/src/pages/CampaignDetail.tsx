import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCampaign } from "@/api/campaigns";
import { cancelDiscoveryJob, getDiscoveryJob, startDiscovery } from "@/api/discovery";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { SCORING_LABELS } from "@/constants/scoring";
import type { CampaignDetail as CampaignDetailType } from "@/types/campaign";
import type { DiscoveryJob } from "@/types/discovery";
import { Play, X, Loader2, CheckCircle2, AlertCircle, Database, HelpCircle, Activity } from "lucide-react";

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>();
  const [campaign, setCampaign] = useState<CampaignDetailType | null>(null);
  const [job, setJob] = useState<DiscoveryJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

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
      const created = await startDiscovery(id);
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
          </div>
          <div className="xl:col-span-4">
            <AppSection title="Scoring weights" testId="campaign-scoring-weights">
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