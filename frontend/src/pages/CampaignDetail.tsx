import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getCampaign } from "@/api/campaigns";
import { cancelDiscoveryJob, getDiscoveryJob, startDiscovery } from "@/api/discovery";
import { Button } from "@/components/ui/button";
import { SCORING_LABELS } from "@/constants/scoring";
import type { CampaignDetail as CampaignDetailType } from "@/types/campaign";
import type { DiscoveryJob } from "@/types/discovery";
import { Play, X, Loader2, CheckCircle2, AlertCircle, BarChart3, Radio, Database, HelpCircle, Activity } from "lucide-react";

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

  if (error && !campaign) return <div className="p-8 text-xs text-red-500 bg-red-50 border border-red-200 m-8 rounded-sm">{error}</div>;
  if (!campaign) {
    return (
      <div className="p-10 flex items-center justify-center min-h-[50vh]">
        <Loader2 className="size-5 animate-spin text-slate-400" />
      </div>
    );
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

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="campaign-detail">
      <Link to="/campaigns" className="inline-flex items-center gap-1 text-xs text-[var(--color-muted)] hover:text-slate-900 transition-colors mb-6">
        ← Campaigns
      </Link>

      {/* Hero Header */}
      <div className="border border-slate-200 bg-white p-6 rounded-sm mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <span className="text-[11px] font-mono uppercase tracking-widest text-[var(--color-muted)] bg-slate-100 px-2 py-0.5 rounded-sm">Campaign Detail</span>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 mt-2" data-testid="campaign-detail-name">
            {campaign.name}
          </h1>
          <p className="text-sm text-[var(--color-muted)] mt-1.5 max-w-xl">{campaign.description}</p>
          <Link
            to={`/campaigns/${campaign.id}/events`}
            className="inline-block mt-3 text-sm font-medium text-slate-700 hover:underline"
            data-testid="campaign-view-events"
          >
            View event results →
          </Link>
        </div>
        
        <div className="flex gap-2 shrink-0">
          <Button 
            type="button" 
            data-testid="run-discovery" 
            disabled={running} 
            onClick={() => void runDiscovery()}
            className="rounded-sm text-sm font-semibold px-4 py-2 flex items-center gap-2 h-9"
          >
            {running ? <Loader2 className="size-3.5 animate-spin" /> : <Play className="size-3.5" fill="currentColor" />}
            {running ? "Running…" : "Run Discovery"}
          </Button>
          {job && !["succeeded", "failed", "partial", "cancelled", "needs_user_action"].includes(job.status) && (
            <Button 
              type="button" 
              variant="ghost" 
              data-testid="cancel-discovery" 
              onClick={() => void cancelJob()}
              className="rounded-sm border border-slate-200 text-sm px-3 h-9 text-slate-700 hover:bg-slate-50 flex items-center gap-1.5"
            >
              <X className="size-3.5" strokeWidth={2} />
              Cancel Job
            </Button>
          )}
        </div>
      </div>

      {error && <p className="mb-6 text-sm text-red-500 bg-red-50 border border-red-200 p-3 rounded-sm">{error}</p>}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Discovery Status & Sources */}
        <div className="lg:col-span-2 space-y-6">
          {/* Active Job State */}
          <section className="bg-white border border-slate-200 p-5 rounded-sm" data-testid="discovery-run">
            <div className="flex items-center gap-2 mb-4 border-b border-slate-100 pb-3">
              <Radio className="size-4 text-slate-500" strokeWidth={1.5} />
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Discovery Engine Log</h2>
            </div>

            {!job ? (
              <div className="py-8 text-center text-slate-400">
                <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                <p className="text-sm">No active or historical discovery execution found. Trigger "Run Discovery" above.</p>
              </div>
            ) : (
              <div className="space-y-4" data-testid="discovery-progress">
                <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                  <span className="text-sm text-slate-500">Pipeline State:</span>
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-sm text-xs font-mono border uppercase ${
                    job.status === "succeeded" ? "bg-emerald-50 text-emerald-700 border-emerald-200" :
                    job.status === "failed" ? "bg-red-50 text-red-700 border-red-200" :
                    "bg-blue-50 text-blue-700 border-blue-200"
                  }`} data-testid="discovery-status">
                    {getStatusIcon(job.status)}
                    {job.status}
                  </span>
                </div>

                {job.progress.sources && (
                  <div className="space-y-2">
                    <p className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Source Crawl Progress</p>
                    <div className="border border-slate-200 rounded-sm divide-y divide-slate-100">
                      {Object.entries(job.progress.sources).map(([sid, s]) => (
                        <div key={sid} className="flex items-center justify-between p-3 text-sm">
                          <span className="font-semibold text-slate-800 flex items-center gap-2">
                            <span className="size-1.5 bg-slate-400 rounded-full"></span>
                            {sid.slice(0, 8)}…
                          </span>
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-slate-500">{s.items_found != null ? `${s.items_found} items found` : ""}</span>
                            <span className="inline-flex items-center gap-1 font-mono text-xs text-slate-700">
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
          </section>
        </div>

        {/* Right Column: Scoring Weights Visual Card */}
        <div>
          <section className="bg-white border border-slate-200 p-5 rounded-sm" data-testid="campaign-scoring-weights">
            <div className="flex items-center gap-2 mb-4 border-b border-slate-100 pb-3">
              <BarChart3 className="size-4 text-slate-500" strokeWidth={1.5} />
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Scoring Configurations</h2>
            </div>
            
            <div className="space-y-4">
              {Object.entries(campaign.scoring_weights).map(([k, v]) => (
                <div key={k} className="space-y-1.5">
                  <div className="flex justify-between text-sm font-medium text-slate-700">
                    <span>{SCORING_LABELS[k] ?? k}</span>
                    <span className="font-mono text-slate-900 font-semibold">{(v * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-slate-100 h-2 rounded-sm overflow-hidden">
                    <div 
                      className="bg-slate-900 h-full rounded-sm" 
                      style={{ width: `${Math.max(0, Math.min(100, v * 100))}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 p-3 bg-slate-50 border border-slate-150 rounded-sm flex items-start gap-2.5 text-xs text-slate-500">
              <HelpCircle className="size-4 text-slate-400 shrink-0 mt-0.5" strokeWidth={1.5} />
              <p>Weights determine how target leads are automatically prioritized inside pipeline streams.</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}