import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createConnector, listConnectors } from "@/api/connectors";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { LIST_PAGE_SIZE } from "@/constants/listPageSize";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { ConnectorView } from "@/types/connector";
import { Plus, ShieldAlert, Key, Chrome, Rss, Link2, Settings2, Database, ShieldCheck } from "lucide-react";

export default function AdminConnectors() {
  const [items, setItems] = useState<ConnectorView[]>([]);
  const [name, setName] = useState("");
  const [domain, setDomain] = useState("");
  const [page, setPage] = useState(1);

  async function refresh() {
    setItems(await listConnectors());
  }

  useEffect(() => {
    void refresh();
  }, []);

  const currentItems = paginateSlice(items, page);

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
      const targetPage = Math.floor(index / LIST_PAGE_SIZE) + 1;
      setPage(targetPage);
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
    <AppPageShell testId="admin-connectors">
      <AppPageHeader
        title="Connector registry"
        subtitle="Governance and connector policy — no live discovery from this screen."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/browser-profiles" className="underline text-slate-600" data-testid="nav-browser-profiles">
              Browser profiles
            </Link>
            <Settings2 className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-4">
        <AppSection title="Add connector">
          
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
        </AppSection>
        </div>

        <div className="xl:col-span-8">
        <AppSection title="Registered connectors" className="flex flex-col">
            <table className="w-full text-sm text-left">
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

          <ListPagination page={page} totalItems={items.length} onPageChange={setPage} testId="admin-connectors-pagination" />
        </AppSection>
        </div>
      </div>
      </div>
    </AppPageShell>
  );
}