import { useEffect, useState } from "react";
import { createConnector, listConnectors } from "@/api/connectors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ConnectorView } from "@/types/connector";
import { Plus, ShieldAlert, Key, Chrome, Rss, Link2, Settings2, Database, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";

export default function AdminConnectors() {
  const [items, setItems] = useState<ConnectorView[]>([]);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const ITEMS_PER_PAGE = 10;

  async function refresh() {
    setItems(await listConnectors());
  }

  useEffect(() => {
    void refresh();
  }, []);

  const totalPages = Math.ceil(items.length / ITEMS_PER_PAGE);
  const indexOfLastItem = currentPage * ITEMS_PER_PAGE;
  const indexOfFirstItem = indexOfLastItem - ITEMS_PER_PAGE;
  const currentItems = items.slice(indexOfFirstItem, indexOfLastItem);

  useEffect(() => {
    if (currentPage > 1 && currentPage > totalPages) {
      setCurrentPage(1);
    }
  }, [items.length, totalPages, currentPage]);

  async function addRss() {
    const newConn = await createConnector({
      name: name || "Events RSS",
      domain: domain || "events.example.com",
      connector_type: "rss",
      authentication_mode: "none",
      enabled: true,
      approved: true,
      policy: { access_mode: "feed", quota_per_day: 500, quota_used_today: 0, valid: true },
    });
    setName("");
    setDomain("");
    
    // Fetch updated list of connectors
    const updatedItems = await listConnectors();
    setItems(updatedItems);

    // Find the index of the newly created connector in the updated list
    const index = updatedItems.findIndex(item => item.id === newConn.id);
    if (index !== -1) {
      // Calculate which page this index corresponds to
      const targetPage = Math.floor(index / ITEMS_PER_PAGE) + 1;
      setCurrentPage(targetPage);
    }
  }

  const getConnectorIcon = (type: string) => {
    switch (type) {
      case "rss":
        return <Rss className="size-3.5 text-amber-600" />;
      case "playwright":
      case "browser":
        return <Chrome className="size-3.5 text-blue-600" />;
      default:
        return <Link2 className="size-3.5 text-slate-500" />;
    }
  };

  const getPolicyStateBadge = (state: string) => {
    const isApproved = state === "approved" || state === "valid" || state === "active";
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-sm text-xs font-mono border ${
        isApproved
          ? "bg-emerald-50 text-emerald-700 border-emerald-200" 
          : "bg-amber-50 text-amber-700 border-amber-200"
      }`}>
        {isApproved ? <ShieldCheck className="size-3.5" /> : <ShieldAlert className="size-3.5" />}
        {state}
      </span>
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto" data-testid="admin-connectors">
      {/* Header */}
      <div className="border-b border-slate-200 pb-5 mb-8">
        <div className="flex items-center gap-3">
          <Settings2 className="size-6 text-slate-700" strokeWidth={1.5} />
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Connector Registry</h1>
        </div>
        <p className="text-sm text-[var(--color-muted)] mt-1.5">Governance and connector policy enforcement — no live discovery.</p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Column: Form Card */}
        <div className="bg-white border border-slate-200 p-6 rounded-sm shadow-sm space-y-5">
          <div className="border-b border-slate-100 pb-2.5">
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Add Connector</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <Label className="text-sm font-semibold text-slate-700">Connector Name</Label>
              <Input 
                data-testid="connector-name" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                placeholder="e.g. TechNews Feed"
                className="mt-1.5 text-sm"
              />
            </div>
            <div>
              <Label className="text-sm font-semibold text-slate-700">Domain URL</Label>
              <Input 
                data-testid="connector-domain" 
                value={domain} 
                onChange={(e) => setDomain(e.target.value)} 
                placeholder="e.g. feed.technews.com"
                className="mt-1.5 text-sm"
              />
            </div>
            
            <Button 
              type="button" 
              data-testid="connector-add" 
              onClick={() => void addRss()}
              className="w-full rounded-sm text-sm font-semibold h-10 flex items-center justify-center gap-1.5"
            >
              <Plus className="size-4.5" strokeWidth={2.5} />
              Add RSS Source
            </Button>
          </div>
        </div>

        {/* Right Column: Registry Table */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-sm overflow-hidden flex flex-col justify-between">
          <div>
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700">Registered Connectors</h2>
            </div>
            
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-xs">
                  <th className="px-5 py-3 font-semibold">Name</th>
                  <th className="px-5 py-3 font-semibold">Type</th>
                  <th className="px-5 py-3 font-semibold">State</th>
                  <th className="px-5 py-3 font-semibold">Secret</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {currentItems.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/20 transition-colors" data-testid="connector-row">
                    <td className="px-5 py-4 font-semibold text-slate-900">
                      <div className="flex flex-col">
                        <span>{c.name}</span>
                        <span className="text-xs text-slate-400 font-mono font-normal mt-0.5">{c.domain}</span>
                      </div>
                    </td>
                    <td className="px-5 py-4 text-slate-600">
                      <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase">
                        {getConnectorIcon(c.connector_type)}
                        {c.connector_type}
                      </span>
                    </td>
                    <td className="px-5 py-4" data-testid="connector-policy-state">
                      {getPolicyStateBadge(c.policy_state)}
                    </td>
                    <td className="px-5 py-4 text-slate-500 font-mono text-xs" data-testid="connector-secret">
                      <span className="inline-flex items-center gap-1.5">
                        <Key className="size-3.5 text-slate-400" />
                        {c.secret_display || "(none)"}
                      </span>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-5 py-10 text-center text-slate-400">
                      <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                      <span>No connectors registered yet.</span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Toolbar */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50/50 px-5 py-3 text-xs">
              <span className="text-slate-500 font-mono">
                Showing {indexOfFirstItem + 1}–{Math.min(indexOfLastItem, items.length)} of {items.length} connectors
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
    </div>
  );
}