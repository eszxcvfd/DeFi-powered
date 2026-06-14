import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getLead, listLeads, patchLead } from "@/api/leads";
import { completeReminder, listReminderQueue, type ReminderQueueItem } from "@/api/reminders";
import { Button } from "@/components/ui/button";
import { LEAD_STAGE_LABELS, type LeadDetail, type LeadSummary } from "@/types/lead";
import { Loader2, Building, User, Clock } from "lucide-react";

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

  if (loading) {
    return (
      <div className="p-10 flex justify-center">
        <Loader2 className="size-5 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1400px] mx-auto" data-testid="leads-pipeline">
      <div className="flex items-center justify-between gap-4 mb-6">
        <h1 className="text-xl font-bold">Lead pipeline</h1>
        <div className="flex gap-2">
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
        </div>
      </div>
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

      <section className="mb-6 border border-slate-200 p-4 rounded-sm bg-white" data-testid="reminder-queue">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2">Due follow-ups</h2>
        {queue.length === 0 ? (
          <p className="text-sm text-slate-500">No due or overdue reminders.</p>
        ) : (
          <ul className="text-sm space-y-2">
            {queue.map((item) => (
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
      </section>

      {view === "table" ? (
        <table className="w-full text-sm border border-slate-200" data-testid="leads-table">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="p-3">Name</th>
              <th className="p-3">Company</th>
              <th className="p-3">Stage</th>
              <th className="p-3">Owner</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr
                key={l.id}
                className="border-t border-slate-100 cursor-pointer hover:bg-slate-50"
                data-testid="lead-row"
                onClick={() => setSelectedId(l.id)}
              >
                <td className="p-3 font-medium">{l.display_name}</td>
                <td className="p-3">{l.company || "—"}</td>
                <td className="p-3">{LEAD_STAGE_LABELS[l.stage] ?? l.stage}</td>
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
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-6 select-none" data-testid="leads-kanban">
          {STAGE_ORDER.map((stage) => {
            const stageLeads = byStage[stage] || [];
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
                  {stageLeads.length === 0 ? (
                    <li className="text-center py-12 text-xs text-slate-400 border border-dashed border-slate-200 rounded-xl bg-slate-50/20">
                      No leads in this stage
                    </li>
                  ) : (
                    stageLeads.map((l) => {
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
                              <div className={`size-7 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold ${getAvatarColor(l.display_name)}`}>
                                {getInitials(l.display_name)}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="font-semibold text-slate-900 text-[14px] leading-tight group-hover:text-black truncate">
                                  {l.display_name}
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
              </div>
            );
          })}
        </div>
      )}

      {detail && (
        <section className="mt-8 border border-slate-200 p-5 rounded-sm bg-white" data-testid="lead-detail-panel">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-700 mb-2">{detail.display_name}</h2>
          <p className="text-sm text-slate-600 mb-4">
            {LEAD_STAGE_LABELS[detail.stage] ?? detail.stage}
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
          <h3 className="text-xs font-bold uppercase text-slate-500 mb-2">Activity</h3>
          <ul className="text-xs text-slate-600 space-y-1" data-testid="lead-activity-list">
            {detail.recent_activity.map((a) => (
              <li key={a.id}>
                <span className="font-mono">{a.kind}</span> — {a.body || a.to_stage} ({a.actor})
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}