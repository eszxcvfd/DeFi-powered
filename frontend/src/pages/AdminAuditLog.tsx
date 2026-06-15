import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, ShieldAlert, ShieldX, Filter, ListFilter, Database } from "lucide-react";
import {
  getAuditEntry,
  getAuditFilterOptions,
  listAuditEntries,
} from "@/api/auditLog";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import type { AuditEntry, AuditFilterOptions } from "@/types/auditLog";

const PAGE_LIMIT = 25;
const ANY = "__any__";

function outcomeBadge(outcome: string) {
  const o = outcome.toLowerCase();
  if (o === "succeeded") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-emerald-50 text-emerald-700 border-emerald-200">
        <ShieldCheck className="size-3" /> succeeded
      </span>
    );
  }
  if (o === "denied" || o === "failed" || o === "expired") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-rose-50 text-rose-700 border-rose-200">
        <ShieldX className="size-3" /> {o}
      </span>
    );
  }
  if (o === "cancelled" || o === "system_recorded") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-amber-50 text-amber-700 border-amber-200">
        <ShieldAlert className="size-3" /> {o}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-slate-50 text-slate-700 border-slate-200">
      {outcome}
    </span>
  );
}

function formatTs(iso: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toISOString().replace("T", " ").slice(0, 19) + "Z";
  } catch {
    return iso;
  }
}

type Filters = {
  actor_id: string;
  actor_type: string;
  action_family: string;
  target_type: string;
  target_id: string;
  outcome: string;
  request_id: string;
};

const EMPTY_FILTERS: Filters = {
  actor_id: "",
  actor_type: "",
  action_family: "",
  target_type: "",
  outcome: "",
  target_id: "",
  request_id: "",
};

function nativeSelect(
  value: string,
  options: string[],
  testId: string,
  onChange: (v: string) => void,
  includeAny = true,
) {
  return (
    <select
      data-testid={testId}
      value={value || ANY}
      onChange={(e) => onChange(e.target.value === ANY ? "" : e.target.value)}
      className="mt-1 text-xs h-9 w-full rounded-sm border border-slate-200 bg-white px-2"
    >
      {includeAny ? <option value={ANY}>Any</option> : null}
      {options.map((v) => (
        <option key={v} value={v}>
          {v}
        </option>
      ))}
    </select>
  );
}

export default function AdminAuditLog() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [items, setItems] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filterOptions, setFilterOptions] = useState<AuditFilterOptions | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<AuditEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const offset = (page - 1) * PAGE_LIMIT;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT));

  const queryParams = useMemo(
    () => ({
      actor_id: filters.actor_id || undefined,
      actor_type: filters.actor_type || undefined,
      action_family: filters.action_family || undefined,
      target_type: filters.target_type || undefined,
      target_id: filters.target_id || undefined,
      outcome: filters.outcome || undefined,
      request_id: filters.request_id || undefined,
      limit: PAGE_LIMIT,
      offset,
    }),
    [filters, offset],
  );

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const out = await listAuditEntries(queryParams);
      setItems(out.items);
      setTotal(out.total);
    } catch (err) {
      setError((err as Error).message || "Failed to load");
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, [queryParams]);

  useEffect(() => {
    getAuditFilterOptions()
      .then(setFilterOptions)
      .catch(() => setFilterOptions(null));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelected(null);
      return;
    }
    getAuditEntry(selectedId)
      .then(setSelected)
      .catch(() => setSelected(null));
  }, [selectedId]);

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setPage(1);
  }

  return (
    <AppPageShell testId="admin-audit-log">
      <AppPageHeader
        title="Audit log"
        subtitle="Tenant-scoped, append-only history of governance-sensitive actions. Read-only."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/connectors" className="underline text-slate-600" data-testid="nav-admin-connectors">
              Connectors
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/browser-profiles" className="underline text-slate-600" data-testid="nav-browser-profiles">
              Browser profiles
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/members" className="underline text-slate-600" data-testid="nav-members">
              Members & invitations
            </Link>
            <Filter className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-3 space-y-4">
            <AppSection title="Filters" testId="audit-filters">
              <div className="space-y-3 text-sm">
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Actor ID
                  </Label>
                  <Input
                    data-testid="filter-actor-id"
                    value={filters.actor_id}
                    onChange={(e) => setFilters((f) => ({ ...f, actor_id: e.target.value }))}
                    placeholder="e.g. admin"
                    className="mt-1 text-xs"
                  />
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Actor type
                  </Label>
                  {nativeSelect(
                    filters.actor_type,
                    filterOptions?.actor_types || [],
                    "filter-actor-type",
                    (v) => setFilters((f) => ({ ...f, actor_type: v })),
                  )}
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Action family
                  </Label>
                  {nativeSelect(
                    filters.action_family,
                    filterOptions?.action_families || [],
                    "filter-action-family",
                    (v) => setFilters((f) => ({ ...f, action_family: v })),
                  )}
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Target type
                  </Label>
                  {nativeSelect(
                    filters.target_type,
                    filterOptions?.target_types || [],
                    "filter-target-type",
                    (v) => setFilters((f) => ({ ...f, target_type: v })),
                  )}
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Target ID
                  </Label>
                  <Input
                    data-testid="filter-target-id"
                    value={filters.target_id}
                    onChange={(e) => setFilters((f) => ({ ...f, target_id: e.target.value }))}
                    placeholder="optional"
                    className="mt-1 text-xs"
                  />
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Outcome
                  </Label>
                  {nativeSelect(
                    filters.outcome,
                    filterOptions?.outcomes || [],
                    "filter-outcome",
                    (v) => setFilters((f) => ({ ...f, outcome: v })),
                  )}
                </div>
                <div>
                  <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                    Request ID
                  </Label>
                  <Input
                    data-testid="filter-request-id"
                    value={filters.request_id}
                    onChange={(e) => setFilters((f) => ({ ...f, request_id: e.target.value }))}
                    placeholder="x-request-id"
                    className="mt-1 text-xs"
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={clearFilters}
                  data-testid="filter-clear"
                  className="w-full text-xs border border-slate-200 mt-2"
                >
                  <ListFilter className="size-3.5" />
                  Clear filters
                </Button>
              </div>
            </AppSection>
          </div>

          <div className="xl:col-span-9 space-y-4">
            <AppSection
              title="Audit entries"
              description={`${total} total · page ${page} of ${totalPages}`}
              testId="audit-list"
            >
              {error ? (
                <p className="text-xs text-rose-700" data-testid="audit-error">
                  {error}
                </p>
              ) : null}
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-[10px]">
                    <th className="px-3 py-2 font-semibold">When</th>
                    <th className="px-3 py-2 font-semibold">Actor</th>
                    <th className="px-3 py-2 font-semibold">Action</th>
                    <th className="px-3 py-2 font-semibold">Target</th>
                    <th className="px-3 py-2 font-semibold">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {items.map((e) => (
                    <tr
                      key={e.id}
                      data-testid="audit-row"
                      onClick={() => setSelectedId(e.id)}
                      className={`cursor-pointer hover:bg-slate-50/40 transition-colors ${
                        selectedId === e.id ? "bg-slate-50" : ""
                      }`}
                    >
                      <td className="px-3 py-2 font-mono text-[11px] text-slate-700">
                        {formatTs(e.occurred_at)}
                      </td>
                      <td className="px-3 py-2 text-slate-800">
                        <div className="flex flex-col">
                          <span className="font-semibold text-[12px]">{e.actor.actor_id}</span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {e.actor.actor_type}
                            {e.actor.role ? ` · ${e.actor.role}` : ""}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        <span className="font-mono text-[11px]">{e.action}</span>
                      </td>
                      <td className="px-3 py-2 text-slate-700">
                        <div className="flex flex-col">
                          <span className="text-[12px]">{e.target.target_id}</span>
                          <span className="text-[10px] font-mono text-slate-500">
                            {e.target.target_type}
                          </span>
                        </div>
                      </td>
                      <td className="px-3 py-2" data-testid="audit-outcome">
                        {outcomeBadge(e.outcome)}
                      </td>
                    </tr>
                  ))}
                  {!loading && items.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-3 py-8 text-center text-slate-400">
                        <Database className="size-7 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                        <span className="text-xs">No audit entries match these filters yet.</span>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>

              <div
                className="flex items-center justify-between gap-2 mt-3 text-xs"
                data-testid="audit-pagination"
              >
                <span className="text-slate-500 font-mono">
                  {total === 0
                    ? "0"
                    : `${offset + 1}–${Math.min(offset + PAGE_LIMIT, total)} of ${total}`}
                </span>
                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    data-testid="audit-prev"
                    className="h-7 px-2.5 border border-slate-200 text-[11px]"
                  >
                    Prev
                  </Button>
                  <span className="px-2 font-mono text-slate-600">
                    {page} / {totalPages}
                  </span>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    data-testid="audit-next"
                    className="h-7 px-2.5 border border-slate-200 text-[11px]"
                  >
                    Next
                  </Button>
                </div>
              </div>
            </AppSection>

            {selected ? (
              <AppSection title="Audit entry detail" testId="audit-detail">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  <DetailRow label="ID" value={selected.id} mono />
                  <DetailRow label="Occurred" value={formatTs(selected.occurred_at)} mono />
                  <DetailRow
                    label="Actor"
                    value={`${selected.actor.actor_id} (${selected.actor.actor_type}${
                      selected.actor.role ? `, ${selected.actor.role}` : ""
                    })`}
                  />
                  <DetailRow label="Action" value={selected.action} mono />
                  <DetailRow label="Family" value={selected.action_family} />
                  <DetailRow
                    label="Target"
                    value={`${selected.target.target_type} · ${selected.target.target_id}`}
                  />
                  <DetailRow label="Outcome" value={selected.outcome} />
                  <DetailRow label="Request ID" value={selected.context.request_id || "—"} mono />
                </div>
                <div className="mt-4">
                  <h3 className="text-[11px] font-mono uppercase tracking-wider text-slate-500 mb-1">
                    Metadata {selected.metadata_redacted ? "(redacted)" : ""}
                  </h3>
                  {selected.metadata_redacted ? (
                    <p
                      className="text-[10px] text-amber-800 mb-1"
                      data-testid="audit-redaction-note"
                    >
                      Secret-bearing fields were removed before persistence. The audit surface
                      never returns raw credentials, tokens, or full cookies.
                    </p>
                  ) : null}
                  <pre
                    data-testid="audit-metadata"
                    className="text-[11px] font-mono bg-slate-50 border border-slate-200 rounded-sm p-3 overflow-x-auto whitespace-pre-wrap break-words"
                  >
                    {JSON.stringify(selected.metadata, null, 2)}
                  </pre>
                </div>
              </AppSection>
            ) : null}
          </div>
        </div>
      </div>
    </AppPageShell>
  );
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="border border-slate-200 rounded-sm bg-white p-2.5">
      <p className="text-[10px] font-mono uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-0.5 ${mono ? "font-mono" : ""} text-slate-800 break-all`}>{value}</p>
    </div>
  );
}
