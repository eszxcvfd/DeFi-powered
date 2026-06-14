export type ReminderQueueItem = {
  id: string;
  lead_id: string;
  lead_display_name: string;
  lead_company: string;
  lead_stage: string;
  owner: string;
  due_date: string;
  state: string;
  last_actor: string;
  last_action_at: string | null;
};

export async function listReminderQueue(): Promise<ReminderQueueItem[]> {
  const r = await fetch("/reminders/queue");
  if (!r.ok) throw new Error("reminder queue failed");
  return r.json();
}

export async function listReminderAlerts(): Promise<
  { reminder_id: string; lead_display_name: string; state: string }[]
> {
  const r = await fetch("/reminders/alerts");
  if (!r.ok) throw new Error("reminder alerts failed");
  return r.json();
}

export async function completeReminder(id: string, note = ""): Promise<ReminderQueueItem> {
  const r = await fetch(`/reminders/${id}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ note }),
  });
  if (!r.ok) throw new Error("complete reminder failed");
  return r.json();
}

export async function rescheduleReminder(id: string, due_date: string, note = ""): Promise<ReminderQueueItem> {
  const r = await fetch(`/reminders/${id}/reschedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ due_date, note }),
  });
  if (!r.ok) throw new Error("reschedule reminder failed");
  return r.json();
}