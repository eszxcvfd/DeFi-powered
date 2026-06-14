import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getLead, listLeads, patchLead, recordLeadOutcome } from "@/api/leads";
import { completeReminder, listReminderQueue, type ReminderQueueItem } from "@/api/reminders";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { ListPagination, paginateSlice } from "@/components/ListPagination";
import { Button } from "@/components/ui/button";
import { latestOutcomeBadgeText } from "@/lib/leadActivityDisplay";
import { leadPrimaryLabel, leadSecondaryLine } from "@/lib/leadDisplay";
import { LEAD_STAGE_LABELS, OUTCOME_TYPE_LABELS, type LeadDetail, type LeadSummary, type LeadActivity } from "@/types/lead";
import { Loader2, Building, User, Clock, CheckCircle2, FileText, ArrowRight, Info } from "lucide-react";

const STAGE_ORDER = [
  "newly_discovered",
  "watched",
  "connected",
  "message_sent",
  "responded",
  "meeting_scheduled",
  "in_discussion",
  "opportunity",
  "not_fit",
];

const STAGE_THEMES: Record<string, { border: string; bg: string; text: string; lightBg: string }> = {
  newly_discovered: { border: "border-t-slate-400/80", bg: "bg-slate-100", text: "text-slate-700", lightBg: "bg-slate-50/50" },
  watched: { border: "border-t-slate-400/80", bg: "bg-slate-100", text: "text-slate-700", lightBg: "bg-slate-50/50" },
  connected: { border: "border-t-sky-400", bg: "bg-sky-100/70", text: "text-sky-700", lightBg: "bg-sky-50/30" },
  message_sent: { border: "border-t-sky-400", bg: "bg-sky-100/70", text: "text-sky-700", lightBg: "bg-sky-50/30" },
  responded: { border: "border-t-amber-400", bg: "bg-amber-100/80", text: "text-amber-700", lightBg: "bg-amber-50/30" },
  meeting_scheduled: { border: "border-t-amber-400", bg: "bg-amber-100/80", text: "text-amber-700", lightBg: "bg-amber-50/30" },
  in_discussion: { border: "border-t-amber-400", bg: "bg-amber-100/80", text: "text-amber-700", lightBg: "bg-amber-50/30" },
  opportunity: { border: "border-t-emerald-500", bg: "bg-emerald-100/80", text: "text-emerald-700", lightBg: "bg-emerald-50/30" },
  not_fit: { border: "border-t-slate-300", bg: "bg-slate-100/60", text: "text-slate-500", lightBg: "bg-slate-50/20" },
};

function getInitials(name: string) {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }
  return name[0].toUpperCase();
}

function getAvatarColor(name: string) {
  const colors = [
    "bg-slate-100 text-slate-700 border border-slate-200/60",
    "bg-sky-50 text-sky-700 border border-sky-100/60",
    "bg-indigo-50 text-indigo-700 border border-indigo-100/60",
    "bg-emerald-50 text-emerald-700 border border-emerald-100/60",
    "bg-amber-50 text-amber-700 border border-amber-100/60",
    "bg-rose-50 text-rose-700 border border-rose-100/60",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % colors.length;
  return colors[index];
}

function renderActivityItem(a: LeadActivity) {
  const when = a.occurred_at || a.created_at;
  const formattedTime = (() => {
    try {
      return new Date(when).toLocaleString();
    } catch {
      return when;
    }
  })();

  const isOutcome = a.kind === "outcome_recorded";
  const isStage = a.kind === "stage_changed";
  const isNote = a.kind === "note_added";

  let IconComponent = Info;
  let iconStyle = "bg-slate-50 text-slate-500 border-slate-200";
  let badgeStyle = "bg-slate-100 text-slate-700 border-slate-200/60";
  let badgeText = a.kind;

  if (isOutcome) {
    IconComponent = CheckCircle2;
    iconStyle = "bg-emerald-50 text-emerald-600 border-emerald-200";
    badgeStyle = "bg-emerald-50 text-emerald-800 border-emerald-200/80";
    const typeLabel = a.outcome_type ? (OUTCOME_TYPE_LABELS[a.outcome_type] ?? a.outcome_type) : "";
    badgeText = `outcome_recorded${typeLabel ? `: ${typeLabel}` : ""}`;
  } else if (isStage) {
    IconComponent = ArrowRight;
    iconStyle = "bg-blue-50 text-blue-600 border-blue-250";
    badgeStyle = "bg-blue-50 text-blue-700 border-blue-200/85";
    badgeText = "stage_changed";
  } else if (isNote) {
    IconComponent = FileText;
    iconStyle = "bg-amber-50 text-amber-600 border-amber-200";
    badgeStyle = "bg-amber-50 text-amber-700 border-amber-200/80";
    badgeText = "note_added";
  }

  return (
    <>
      {/* Centered Timeline Icon */}
      <div className={`absolute -left-3 top-0.5 size-6 rounded-full flex items-center justify-center bg-white border shadow-xs shrink-0 ${iconStyle}`}>
        <IconComponent className="size-3.5" />
      </div>

      {/* Item Content Header */}
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-slate-500 mb-1">
        <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold border ${badgeStyle}`}>
          {badgeText}
        </span>
        <span className="font-medium text-slate-700">{a.actor}</span>
        <span className="text-slate-400">·</span>
        <span>{formattedTime}</span>
      </div>

      {/* Item Body details */}
      {isOutcome && (
        <>
          {(() => {
            const isGeneric = a.body ? /^Recorded \w+ outcome$/i.test(a.body.trim()) : true;
            if (!isGeneric && a.body) {
              return (
                <div className="mt-1 text-[12px] text-slate-750 bg-emerald-50/30 border border-emerald-100/60 rounded-xl p-3 font-normal shadow-2xs leading-relaxed max-w-2xl">
                  {a.body}
                </div>
              );
            }
            return null;
          })()}
        </>
      )}

      {isStage && (
        <div className="mt-1 flex items-center gap-1.5 text-[12px] text-slate-700 font-medium">
          <span className="px-1.5 py-0.5 bg-slate-50 rounded-md text-slate-600 border border-slate-200/50">
            {LEAD_STAGE_LABELS[a.from_stage] ?? a.from_stage}
          </span>
          <ArrowRight className="size-3.5 text-slate-400 shrink-0" />
          <span className="px-1.5 py-0.5 bg-slate-50 rounded-md text-slate-800 border border-slate-200 font-semibold">
            {LEAD_STAGE_LABELS[a.to_stage] ?? a.to_stage}
          </span>
        </div>
      )}

      {isNote && (
        <div className="mt-1 text-[12px] text-slate-700 bg-amber-50/20 border border-amber-100/50 rounded-xl p-3 font-normal italic shadow-2xs leading-relaxed max-w-2xl">
          {a.body || "—"}
        </div>
      )}

      {!isOutcome && !isStage && !isNote && a.body && (
        <div className="mt-1 text-[12px] text-slate-600 leading-relaxed">
          {a.body}
        </div>
      )}
    </>
  );
}

export default function LeadsPipelinePage() {
  const [leads, setLeads] = useState<LeadSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [view, setView] = useState<"table" | "kanban">("table");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<ReminderQueueItem[]>([]);
  const [followUp, setFollowUp] = useState("");
  const [outcomeType, setOutcomeType] = useState("contact");
  const [outcomeNote, setOutcomeNote] = useState("");
  const [outcomeSavedFlash, setOutcomeSavedFlash] = useState<string | null>(null);
  const [leadsPage, setLeadsPage] = useState(1);
  const [reminderPage, setReminderPage] = useState(1);
  const [kanbanPages, setKanbanPages] = useState<Record<string, number>>({});

  const refresh = () =>
    Promise.all([listLeads(), listReminderQueue()])
      .then(([leadRows, q]) => {
        setLeads(leadRows);
        setQueue(q);
      })
      .catch((e) => setError(String(e)));

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    getLead(selectedId)
      .then((d) => {
        setDetail(d);
        setFollowUp(d.follow_up_date ?? "");
      })
      .catch((e) => setError(String(e)));
  }, [selectedId]);

  useEffect(() => {
    if (!detail || !outcomeSavedFlash) return;
    document.getElementById("lead-detail-panel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [detail, outcomeSavedFlash]);

  const pagedLeads = useMemo(() => paginateSlice(leads, leadsPage), [leads, leadsPage]);
  const pagedQueue = useMemo(() => paginateSlice(queue, reminderPage), [queue, reminderPage]);

  const byStage = useMemo(() => {
    const map: Record<string, LeadSummary[]> = {};
    for (const s of STAGE_ORDER) map[s] = [];
    for (const l of leads) {
      const key = STAGE_ORDER.includes(l.stage) ? l.stage : "newly_discovered";
      map[key].push(l);
    }
    return map;
  }, [leads]);

  async function moveStage(lead: LeadSummary, stage: string) {
    setSaving(true);
    try {
      const updated = await patchLead(lead.id, { stage });
      setDetail(updated);
      setSelectedId(updated.id);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function submitNote() {
    if (!selectedId || !note.trim()) return;
    setSaving(true);
    try {
      const updated = await patchLead(selectedId, { activity_note: note.trim() });
      setDetail(updated);
      setNote("");
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function submitOutcome() {
    if (!selectedId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await recordLeadOutcome(selectedId, {
        outcome_type: outcomeType,
        notes: outcomeNote.trim() || undefined,
      });
      setDetail(updated);
      setOutcomeNote("");
      const label =
        OUTCOME_TYPE_LABELS[outcomeType] ?? outcomeType;
      setOutcomeSavedFlash(`Saved: ${label} outcome`);
      window.setTimeout(() => setOutcomeSavedFlash(null), 5000);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  return (
    <AppPageShell testId="leads-pipeline">
      <AppPageHeader
        title="Lead pipeline"
        subtitle="Stages, outcomes, and follow-up reminders."
        actions={
          <>
            <Button
              type="button"
              size="sm"
              variant={view === "table" ? "default" : "ghost"}
              data-testid="leads-view-table"
              onClick={() => setView("table")}
            >
              Table
            </Button>
            <Button
              type="button"
              size="sm"
              variant={view === "kanban" ? "default" : "ghost"}
              data-testid="leads-view-kanban"
              onClick={() => setView("kanban")}
            >
              Kanban
            </Button>
          </>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
      {error && (
        <p className="text-sm text-red-600 mb-4" data-testid="leads-error">
          {error}
        </p>
      )}
      {outcomeSavedFlash && (
        <p
          className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-sm mb-4"
          data-testid="lead-outcome-saved-flash"
        >
          {outcomeSavedFlash}. See <strong>Latest outcome</strong> and <strong>Outcomes</strong> below the list.
        </p>
      )}

      <AppSection title="Due follow-ups" testId="reminder-queue" className="mb-6">
        {queue.length === 0 ? (
          <p className="text-sm text-slate-500">No due or overdue reminders.</p>
        ) : (
          <ul className="text-sm space-y-2">
            {pagedQueue.map((item) => (
              <li key={item.id} className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{item.lead_display_name}</span>
                <span className="text-xs text-slate-500">
                  {item.due_date} · {item.state}
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  data-testid="reminder-complete"
                  disabled={saving}
                  onClick={async () => {
                    setSaving(true);
                    try {
                      await completeReminder(item.id);
                      await refresh();
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setSaving(false);
                    }
                  }}
                >
                  Complete
                </Button>
              </li>
            ))}
          </ul>
        )}
        <ListPagination
          page={reminderPage}
          totalItems={queue.length}
          onPageChange={setReminderPage}
          testId="reminder-queue-pagination"
        />
      </AppSection>

      {view === "table" ? (
        <>
        <table className="w-full text-sm border border-slate-200" data-testid="leads-table">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="p-3">Event / lead</th>
              <th className="p-3">Organizer · region</th>
              <th className="p-3">Stage</th>
              <th className="p-3">Owner</th>
            </tr>
          </thead>
          <tbody>
            {pagedLeads.map((l) => (
              <tr
                key={l.id}
                className="border-t border-slate-100 cursor-pointer hover:bg-slate-50"
                data-testid="lead-row"
                onClick={() => setSelectedId(l.id)}
              >
                <td className="p-3">
                  <p className="font-medium text-slate-900">{leadPrimaryLabel(l)}</p>
                  {l.event_title && l.display_name !== leadPrimaryLabel(l) ? (
                    <p className="text-xs text-slate-500 mt-0.5 truncate max-w-md">{l.display_name}</p>
                  ) : null}
                </td>
                <td className="p-3 text-slate-600">{leadSecondaryLine(l) || "—"}</td>
                <td className="p-3">
                  {LEAD_STAGE_LABELS[l.stage] ?? l.stage}
                  {l.latest_outcome ? (
                    <span
                      className="ml-2 text-[10px] font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded-sm"
                      data-testid="lead-row-latest-outcome"
                    >
                      {latestOutcomeBadgeText(l.latest_outcome.outcome_type)}
                    </span>
                  ) : null}
                </td>
                <td className="p-3">
                  {l.owner || "—"}
                  {l.reminder?.state === "due" || l.reminder?.state === "overdue" ? (
                    <span className="ml-2 text-xs text-amber-700" data-testid="lead-reminder-badge">
                      {l.reminder.state}
                    </span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <ListPagination page={leadsPage} totalItems={leads.length} onPageChange={setLeadsPage} testId="leads-table-pagination" />
        </>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-6 select-none" data-testid="leads-kanban">
          {STAGE_ORDER.map((stage) => {
            const stageLeads = byStage[stage] || [];
            const stagePage = kanbanPages[stage] ?? 1;
            const pagedStageLeads = paginateSlice(stageLeads, stagePage);
            const theme = STAGE_THEMES[stage] || STAGE_THEMES.newly_discovered;
            return (
              <div
                key={stage}
                className={`flex-shrink-0 w-80 ${theme.lightBg} border-t-2 ${theme.border} border-x border-b border-slate-200/60 rounded-xl p-4 flex flex-col min-h-[550px] shadow-xs`}
              >
                {/* Column Header */}
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-slate-200/40">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 truncate pr-2">
                    {LEAD_STAGE_LABELS[stage]}
                  </h3>
                  <span className={`text-[10px] font-bold ${theme.bg} ${theme.text} px-2 py-0.5 rounded-full shrink-0`}>
                    {stageLeads.length}
                  </span>
                </div>

                {/* Cards List */}
                <ul className="space-y-3 flex-1 overflow-y-auto max-h-[600px] pr-1">
                  {pagedStageLeads.length === 0 ? (
                    <li className="text-center py-12 text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl bg-slate-50/20">
                      No leads on this page
                    </li>
                  ) : (
                    pagedStageLeads.map((l) => {
                      const isSelected = selectedId === l.id;
                      const isOverdue = l.reminder?.state === "overdue" || l.reminder?.state === "due";

                      return (
                        <li key={l.id}>
                          <button
                            type="button"
                            className={`w-full text-left p-4 bg-white border rounded-xl shadow-xs hover:shadow-md hover:border-slate-350 transition-all duration-200 relative group cursor-pointer active:scale-[0.98] overflow-hidden ${
                              isSelected
                                ? "border-slate-900 ring-1 ring-slate-900 bg-slate-50/30 shadow-sm before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-slate-900 before:rounded-l-xl"
                                : "border-slate-200/80"
                            }`}
                            data-testid="lead-kanban-card"
                            onClick={() => setSelectedId(l.id)}
                          >
                            {/* Monogram Avatar & Lead Name & Job Title */}
                            <div className="flex items-start gap-2.5 mb-2.5">
                              <div className={`size-7 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold ${getAvatarColor(leadPrimaryLabel(l))}`}>
                                {getInitials(leadPrimaryLabel(l))}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="font-semibold text-slate-900 text-[14px] leading-tight group-hover:text-black truncate">
                                  {leadPrimaryLabel(l)}
                                </div>
                                {l.title && (
                                  <span className="inline-block mt-0.5 text-[10px] font-medium text-slate-500 truncate max-w-full">
                                    {l.title}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Badges / Tags */}
                            {(l.company || l.discovery_source) ? (
                              <div className="flex flex-wrap gap-1.5 mb-3">
                                {l.company && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-50 text-slate-600 border border-slate-200/50 text-[10px] font-medium max-w-full">
                                    <Building className="size-2.5 text-slate-400 shrink-0" />
                                    <span className="truncate">{l.company}</span>
                                  </span>
                                )}
                                {l.discovery_source && (
                                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-indigo-50/50 text-indigo-700 border border-indigo-100/50 text-[10px] font-medium max-w-full">
                                    <span className="w-1 h-1 rounded-full bg-indigo-500 shrink-0" />
                                    <span className="truncate">{l.discovery_source}</span>
                                  </span>
                                )}
                                {l.latest_outcome && (
                                  <span
                                    className="inline-flex px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200/80 text-[10px] font-semibold"
                                    data-testid="lead-kanban-outcome-badge"
                                  >
                                    {latestOutcomeBadgeText(l.latest_outcome.outcome_type)}
                                  </span>
                                )}
                              </div>
                            ) : (
                              <div className="h-2" />
                            )}

                            {/* Card Footer */}
                            <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-slate-100 text-[11px] text-slate-400">
                              <div className="flex items-center gap-1 min-w-0 max-w-[55%]">
                                <User className="size-3 text-slate-400 shrink-0" />
                                <span className="truncate" title={`Owner: ${l.owner || "Unassigned"}`}>
                                  {l.owner || "Unassigned"}
                                </span>
                              </div>

                              {l.follow_up_date && (
                                <div className="flex items-center gap-1.5 shrink-0">
                                  {isOverdue && (
                                    <span className="relative flex h-1.5 w-1.5">
                                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                                      <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span>
                                    </span>
                                  )}
                                  <div
                                    className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${
                                      isOverdue
                                        ? "bg-amber-50 text-amber-700 border-amber-200"
                                        : "bg-slate-50 text-slate-600 border-slate-100"
                                    }`}
                                    title={`Follow-up date: ${l.follow_up_date}`}
                                  >
                                    <Clock className="size-2.5 shrink-0" />
                                    <span>{l.follow_up_date}</span>
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Selection Dot */}
                            {isSelected && (
                              <div className="absolute top-4 right-4 w-1.5 h-1.5 rounded-full bg-slate-900" />
                            )}
                          </button>
                        </li>
                      );
                    })
                  )}
                </ul>
                <ListPagination
                  page={stagePage}
                  totalItems={stageLeads.length}
                  onPageChange={(p) => setKanbanPages((prev) => ({ ...prev, [stage]: p }))}
                  testId={`leads-kanban-pagination-${stage}`}
                  className="mt-2 pt-2 border-t-0"
                />
              </div>
            );
          })}
        </div>
      )}

      {detail && (
        <section
          className="mt-8 border border-slate-200 p-5 rounded-sm bg-white scroll-mt-6"
          data-testid="lead-detail-panel"
          id="lead-detail-panel"
        >
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-2">{leadPrimaryLabel(detail)}</h2>
          <p className="text-xs text-slate-500 mb-2">{leadSecondaryLine(detail)}</p>
          <p className="text-sm text-slate-600 mb-4">
            {LEAD_STAGE_LABELS[detail.stage] ?? detail.stage}
            {detail.latest_outcome && (
              <span
                className="ml-2 text-xs font-mono text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-sm"
                data-testid="lead-latest-outcome"
              >
                Latest outcome: {OUTCOME_TYPE_LABELS[detail.latest_outcome.outcome_type] ?? detail.latest_outcome.outcome_type}
                {detail.latest_outcome.notes ? ` — ${detail.latest_outcome.notes}` : ""}
              </span>
            )}
            {detail.event_id && (
              <>
                {" · "}
                <Link to={`/events/${detail.event_id}`} className="underline">
                  Event
                </Link>
              </>
            )}
          </p>
          <div className="mb-4 flex items-center gap-2 text-sm">
            <label className="text-xs uppercase text-slate-500">Follow-up date</label>
            <input
              type="date"
              className="border border-slate-200 rounded-sm px-2 py-1"
              data-testid="lead-follow-up-date"
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              onBlur={async () => {
                if (!selectedId) return;
                setSaving(true);
                try {
                  const updated = await patchLead(selectedId, {
                    follow_up_date: followUp || null,
                  });
                  setDetail(updated);
                  await refresh();
                } catch (e) {
                  setError(String(e));
                } finally {
                  setSaving(false);
                }
              }}
            />
            {detail.reminder?.has_reminder && (
              <span className="text-xs text-slate-600" data-testid="lead-reminder-summary">
                Reminder: {detail.reminder.state}
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-2 mb-4">
            {STAGE_ORDER.filter((s) => s !== detail.stage).slice(0, 4).map((s) => (
              <Button
                key={s}
                type="button"
                size="sm"
                variant="ghost"
                disabled={saving}
                data-testid="lead-move-stage"
                onClick={() => moveStage(detail, s)}
              >
                → {LEAD_STAGE_LABELS[s]}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2 mb-4 p-3 border border-slate-200 rounded-sm bg-slate-50/50" data-testid="lead-record-outcome">
            <span className="text-xs uppercase text-slate-500 w-full sm:w-auto">Record outcome</span>
            <select
              className="border border-slate-200 rounded-sm px-2 py-1 text-sm bg-white"
              data-testid="lead-outcome-type"
              value={outcomeType}
              onChange={(e) => setOutcomeType(e.target.value)}
            >
              {Object.entries(OUTCOME_TYPE_LABELS).map(([k, label]) => (
                <option key={k} value={k}>
                  {label}
                </option>
              ))}
            </select>
            <input
              className="flex-1 min-w-[120px] border border-slate-200 rounded-sm px-3 py-1.5 text-sm"
              placeholder="Outcome notes (optional)"
              data-testid="lead-outcome-notes"
              value={outcomeNote}
              onChange={(e) => setOutcomeNote(e.target.value)}
            />
            <Button type="button" size="sm" disabled={saving} data-testid="lead-record-outcome-submit" onClick={submitOutcome}>
              Save outcome
            </Button>
          </div>
          <div className="flex gap-2 mb-4">
            <input
              className="flex-1 border border-slate-200 rounded-sm px-3 py-2 text-sm"
              placeholder="Quick note"
              data-testid="lead-quick-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <Button type="button" size="sm" disabled={saving} data-testid="lead-add-note" onClick={submitNote}>
              Add note
            </Button>
          </div>
          <h3 className="text-xs font-bold uppercase text-slate-500 mb-4">Timeline</h3>
          <div className="pl-3 pr-1">
            <ul className="relative border-l border-slate-200/80 space-y-6" data-testid="lead-activity-list">
              {detail.recent_activity.length === 0 ? (
                <li className="text-slate-400 pl-4 text-xs">No activity yet.</li>
              ) : (
                detail.recent_activity.map((a) => {
                  const isOutcome = a.kind === "outcome_recorded";
                  return (
                    <li
                      key={a.id}
                      className="relative pl-7 text-xs"
                      data-testid={isOutcome ? "lead-activity-outcome" : undefined}
                    >
                      {renderActivityItem(a)}
                    </li>
                  );
                })
              )}
            </ul>
          </div>
        </section>
      )}
      </div>
    </AppPageShell>
  );
}