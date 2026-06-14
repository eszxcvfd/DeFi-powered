import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCampaigns } from "@/api/campaigns";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { Button } from "@/components/ui/button";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import type { CampaignSummary } from "@/types/campaign";
import { Plus, Briefcase, Calendar, ArrowRight, Target, ShieldCheck, Activity } from "lucide-react";

export default function CampaignList() {
  const [items, setItems] = useState<CampaignSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    listCampaigns()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  const totalCampaigns = items.length;
  const activeCampaigns = items.filter((c) => c.status === "active").length;

  const currentItems = paginateSlice(items, page);

  return (
    <AppPageShell testId="campaign-list">
      <AppPageHeader
        title="Campaigns"
        subtitle="Configure and manage lead discovery pipelines."
        actions={
          <Link to="/campaigns/new">
            <Button type="button" className="rounded-sm flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 h-8">
              <Plus className="size-3.5" strokeWidth={2} />
              New campaign
            </Button>
          </Link>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        {error && (
          <p className="mb-4 text-xs text-red-600 bg-red-50 border border-red-100 p-3 rounded-lg">{error}</p>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <AppSection title="Total pipelines" className="!shadow-none">
            <div className="flex items-center justify-between -mt-2">
              <p className="text-2xl font-bold text-slate-900 tabular-nums">{totalCampaigns}</p>
              <Target className="size-7 text-slate-300" strokeWidth={1.5} />
            </div>
          </AppSection>
          <AppSection title="Active discovery" className="!shadow-none">
            <div className="flex items-center justify-between -mt-2">
              <p className="text-2xl font-bold text-slate-900 tabular-nums">{activeCampaigns}</p>
              <Activity className="size-7 text-slate-300" strokeWidth={1.5} />
            </div>
          </AppSection>
          <AppSection title="System" className="!shadow-none">
            <div className="flex items-center justify-between -mt-2">
              <div className="flex items-center gap-1.5">
                <span className="inline-block size-2 bg-emerald-500 rounded-full animate-pulse" />
                <span className="text-sm font-semibold text-slate-700">Healthy</span>
              </div>
              <ShieldCheck className="size-7 text-slate-300" strokeWidth={1.5} />
            </div>
          </AppSection>
        </div>

        <AppSection title="All campaigns" description="Open a row to run discovery and review events.">
          <div className="overflow-x-auto -mx-4 px-0 sm:mx-0">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-slate-100 text-slate-500 font-mono uppercase tracking-wider text-xs">
                  <th className="px-2 py-3 font-semibold">Campaign</th>
                  <th className="px-2 py-3 font-semibold">Created by</th>
                  <th className="px-2 py-3 font-semibold">Industry</th>
                  <th className="px-2 py-3 font-semibold">Status</th>
                  <th className="px-2 py-3 font-semibold">Updated</th>
                  <th className="px-2 py-3 text-right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentItems.map((c) => (                  <tr key={c.id} className="hover:bg-slate-50/80" data-testid="campaign-list-item">
                    <td className="px-2 py-3 font-semibold text-slate-900">
                      <Link
                        to={`/campaigns/${c.id}`}
                        className="hover:underline flex items-center gap-2"
                        style={{ paddingLeft: `${(c.depth ?? 0) * 16}px` }}
                      >
                        <Target className="size-3.5 text-slate-500 shrink-0" strokeWidth={1.5} />
                        <span className="min-w-0">
                          {c.name}
                          {c.child_count > 0 && (
                            <span className="ml-2 text-[10px] font-mono font-normal text-violet-600">
                              {c.child_count} child{c.child_count !== 1 ? "ren" : ""}
                            </span>
                          )}
                        </span>
                      </Link>
                      {c.parent_name && (
                        <p
                          className="text-[10px] text-slate-400 mt-0.5 font-mono"
                          style={{ paddingLeft: `${(c.depth ?? 0) * 16 + 22}px` }}
                        >
                          under {c.parent_name}
                        </p>
                      )}
                    </td>
                    <td className="px-2 py-3 text-xs text-slate-600">
                      <span className="font-mono block">{c.created_by_actor}</span>
                      <span
                        className={`inline-block mt-1 px-1.5 py-0.5 rounded-sm border text-[10px] ${
                          c.creation_source === "playwright"
                            ? "bg-violet-50 text-violet-700 border-violet-200"
                            : c.creation_source === "automation_root"
                              ? "bg-slate-100 text-slate-600 border-slate-200"
                              : "bg-emerald-50 text-emerald-800 border-emerald-200"
                        }`}
                      >
                        {c.creation_source_label}
                      </span>
                    </td>
                    <td className="px-2 py-3 text-slate-600">
                      <span className="inline-flex items-center gap-1.5">
                        <Briefcase className="size-3 text-slate-400" strokeWidth={1.5} />
                        {c.target_industry}
                      </span>
                    </td>
                    <td className="px-2 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono border ${
                          c.status === "active"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-slate-50 text-slate-600 border-slate-200"
                        }`}
                      >
                        {c.status || "inactive"}
                      </span>
                    </td>
                    <td className="px-2 py-3 text-slate-500 text-xs">
                      <span className="inline-flex items-center gap-1.5">
                        <Calendar className="size-3 text-slate-400" strokeWidth={1.5} />
                        {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "—"}
                      </span>
                    </td>
                    <td className="px-2 py-3 text-right">
                      <Link to={`/campaigns/${c.id}`}>
                        <Button
                          variant="ghost"
                          className="size-7 p-0 rounded-sm inline-flex items-center justify-center hover:bg-slate-100 text-slate-700"
                        >
                          <ArrowRight className="size-3.5" strokeWidth={1.5} />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && !error && (
                  <tr>
                    <td colSpan={6} className="px-2 py-10 text-center text-slate-400">
                      <Target className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                      <p className="text-sm">No campaigns yet.</p>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <ListPagination page={page} totalItems={items.length} onPageChange={setPage} testId="campaign-list-pagination" />
        </AppSection>
      </div>
    </AppPageShell>
  );
}