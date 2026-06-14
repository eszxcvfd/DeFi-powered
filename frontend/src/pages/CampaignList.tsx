import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listCampaigns } from "@/api/campaigns";
import { Button } from "@/components/ui/button";
import type { CampaignSummary } from "@/types/campaign";
import { Plus, Briefcase, Calendar, ArrowRight, Target, ShieldCheck, Activity, ChevronLeft, ChevronRight } from "lucide-react";

export default function CampaignList() {
  const [items, setItems] = useState<CampaignSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const ITEMS_PER_PAGE = 10;

  useEffect(() => {
    listCampaigns()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  // Compute stats for visual dashboard representation
  const totalCampaigns = items.length;
  const activeCampaigns = items.filter(c => c.status === "active").length;

  const totalPages = Math.ceil(items.length / ITEMS_PER_PAGE);
  const indexOfLastItem = currentPage * ITEMS_PER_PAGE;
  const indexOfFirstItem = indexOfLastItem - ITEMS_PER_PAGE;
  const currentItems = items.slice(indexOfFirstItem, indexOfLastItem);

  useEffect(() => {
    if (currentPage > 1 && currentPage > totalPages) {
      setCurrentPage(1);
    }
  }, [items.length, totalPages, currentPage]);

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="campaign-list">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-5 mb-6">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">Campaigns</h1>
          <p className="text-xs text-[var(--color-muted)] mt-1">Configure and manage lead discovery pipelines.</p>
        </div>
        <Link to="/campaigns/new">
          <Button type="button" className="rounded-sm flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 h-8">
            <Plus className="size-3.5" strokeWidth={2} />
            New campaign
          </Button>
        </Link>
      </div>

      {error && <p className="mb-4 text-xs text-red-500 bg-red-50 border border-red-200 p-3 rounded-sm">{error}</p>}

      {/* Visual Analytics Grid (Icons & Minimal Text) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-[var(--color-card)] border border-slate-200 p-4 rounded-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-[var(--color-muted)] font-mono">Total Pipelines</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{totalCampaigns}</h3>
          </div>
          <Target className="size-7 text-slate-400" strokeWidth={1.5} />
        </div>
        
        <div className="bg-[var(--color-card)] border border-slate-200 p-4 rounded-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-[var(--color-muted)] font-mono">Active Discovery</p>
            <h3 className="text-2xl font-bold text-slate-900 mt-1">{activeCampaigns}</h3>
          </div>
          <Activity className="size-7 text-slate-400" strokeWidth={1.5} />
        </div>

        <div className="bg-[var(--color-card)] border border-slate-200 p-4 rounded-sm flex items-center justify-between">
          <div>
            <p className="text-[11px] uppercase tracking-wider text-[var(--color-muted)] font-mono">System Integrity</p>
            <div className="flex items-center gap-1.5 mt-1.5">
              <span className="inline-block size-2 bg-emerald-500 rounded-full animate-pulse"></span>
              <span className="text-xs font-semibold text-slate-700">Healthy</span>
            </div>
          </div>
          <ShieldCheck className="size-7 text-slate-400" strokeWidth={1.5} />
        </div>
      </div>

      {/* Main Table View */}
      <div className="bg-[var(--color-card)] border border-slate-200 rounded-sm overflow-hidden flex flex-col justify-between">
        <table className="w-full text-sm text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-xs">
              <th className="px-5 py-3 font-semibold">Campaign Name</th>
              <th className="px-5 py-3 font-semibold">Created by</th>
              <th className="px-5 py-3 font-semibold">Target Industry</th>
              <th className="px-5 py-3 font-semibold">Status</th>
              <th className="px-5 py-3 font-semibold">Last Updated</th>
              <th className="px-5 py-3 text-right"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {currentItems.map((c) => (
              <tr key={c.id} className="hover:bg-slate-50/50 transition-colors" data-testid="campaign-list-item">
                <td className="px-5 py-4 font-semibold text-slate-900">
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
                    <p className="text-[10px] text-slate-400 mt-0.5 font-mono" style={{ paddingLeft: `${(c.depth ?? 0) * 16 + 22}px` }}>
                      under {c.parent_name}
                    </p>
                  )}
                </td>
                <td className="px-5 py-4 text-xs text-slate-600">
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
                <td className="px-5 py-4 text-slate-600">
                  <span className="inline-flex items-center gap-1.5">
                    <Briefcase className="size-3 text-slate-400" strokeWidth={1.5} />
                    {c.target_industry}
                  </span>
                </td>
                <td className="px-5 py-4">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-mono border ${
                    c.status === "active" 
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200" 
                      : "bg-slate-50 text-slate-600 border-slate-200"
                  }`}>
                    {c.status || "inactive"}
                  </span>
                </td>
                <td className="px-5 py-4 text-slate-500">
                  <span className="inline-flex items-center gap-1.5">
                    <Calendar className="size-3 text-slate-400" strokeWidth={1.5} />
                    {c.updated_at ? new Date(c.updated_at).toLocaleDateString() : "-"}
                  </span>
                </td>
                <td className="px-5 py-4 text-right">
                  <Link to={`/campaigns/${c.id}`}>
                    <Button variant="ghost" className="size-7 p-0 rounded-sm inline-flex items-center justify-center hover:bg-slate-100 text-slate-700">
                      <ArrowRight className="size-3.5" strokeWidth={1.5} />
                    </Button>
                  </Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && !error && (
              <tr>
                <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                  <Target className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                  <p className="text-sm">No active discovery pipelines created yet.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination Toolbar */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50/50 px-5 py-3 text-xs">
            <span className="text-slate-500 font-mono">
              Showing {indexOfFirstItem + 1}–{Math.min(indexOfLastItem, items.length)} of {items.length} campaigns
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage(currentPage - 1)}
                className="h-7 px-2.5 rounded-sm border border-slate-200 disabled:opacity-40 text-slate-700 hover:bg-slate-100 flex items-center gap-1 font-semibold text-[11px]"
              >
                <ChevronLeft className="size-3.5" />
                Previous
              </Button>
              <span className="px-2 text-slate-600 font-mono text-[11px]">
                {currentPage} / {totalPages}
              </span>
              <Button
                variant="ghost"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage(currentPage + 1)}
                className="h-7 px-2.5 rounded-sm border border-slate-200 disabled:opacity-40 text-slate-700 hover:bg-slate-100 flex items-center gap-1 font-semibold text-[11px]"
              >
                Next
                <ChevronRight className="size-3.5" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}