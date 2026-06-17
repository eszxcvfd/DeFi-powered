import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Radio,
  FileText,
  Kanban,
  Monitor,
  Settings,
  Sparkles,
  LogOut,
  UserCircle2,
  Calendar,
} from "lucide-react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { listReminderAlerts } from "@/api/reminders";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/AuthProvider";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";

const nav = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
  { label: "Campaigns", to: "/campaigns", icon: Radio, end: false },
  { label: "Events", to: "/events", icon: FileText, end: true },
  { label: "Leads", to: "/leads", icon: Kanban, end: true },
  { label: "Browser session", to: "/browser", icon: Monitor, end: true },
  { label: "Calendar exports", to: "/settings/calendar-exports", icon: Calendar, end: true },
  { label: "Admin", to: "/admin", icon: Settings, end: true },
];

export default function AppLayout() {
  const [alerts, setAlerts] = useState<{ lead_display_name: string; state: string }[]>([]);
  const { session, signOut } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    listReminderAlerts()
      .then(setAlerts)
      .catch(() => setAlerts([]));
  }, []);

  async function handleSignOut() {
    await signOut();
    navigate("/sign-in", { replace: true });
  }

  return (
    <div className="h-screen w-screen flex bg-[var(--color-background)] overflow-hidden">
      <aside className="w-60 border-r border-[var(--color-border)] bg-[var(--color-card)] p-5 flex flex-col gap-1.5 shrink-0 overflow-y-auto">
        <div className="mb-8 px-2 flex items-center gap-2">
          <div className="size-6 bg-slate-900 text-white flex items-center justify-center rounded-sm font-mono font-bold text-sm">
            L
          </div>
          <div>
            <p className="text-[11px] font-mono uppercase tracking-[0.2em] leading-none text-[var(--color-muted)]">LiveLead</p>
            <h1 className="text-sm font-bold tracking-tight text-slate-900 mt-1">Discovery Portal</h1>
          </div>
        </div>

        <nav className="flex-1 flex flex-col gap-1">
          {nav.map(({ label, to, icon: Icon, end }) => (
            <NavLink key={label} to={to} end={end}>
              {({ isActive }) => (
                <Button
                  variant="ghost"
                  className={`justify-start w-full text-left rounded-sm gap-2.5 px-3 py-2 text-sm font-medium tracking-wide transition-all ${
                    isActive
                      ? "bg-slate-100 text-slate-900 border-l-2 border-slate-900 pl-2"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                  }`}
                >
                  <Icon className="size-4 shrink-0" strokeWidth={1.5} />
                  {label}
                </Button>
              )}
            </NavLink>
          ))}
        </nav>

        {session ? (
          <div
            className="mt-3 p-3 bg-white border border-slate-200/70 rounded-sm"
            data-testid="current-user-card"
          >
            <div className="flex items-center gap-2">
              <UserCircle2 className="size-4 text-slate-700" strokeWidth={1.5} />
              <p
                className="text-xs font-semibold text-slate-800 truncate"
                data-testid="current-user-email"
              >
                {session.email}
              </p>
            </div>
            <p className="text-[10px] font-mono text-slate-500 mt-0.5">
              role: <span data-testid="current-user-role">{session.role}</span>
            </p>
            <p className="text-[10px] font-mono text-slate-500">
              org: <span data-testid="current-user-org">{session.organization_id.slice(0, 8)}…</span>
            </p>
            <div className="mt-2.5 pt-2.5 border-t border-slate-100">
              <LocaleSwitcher compact={true} />
            </div>
            <Button
              variant="ghost"
              onClick={handleSignOut}
              data-testid="sign-out-button"
              className="mt-2.5 w-full h-7 text-[11px] border border-slate-200"
            >
              <LogOut className="size-3.5" />
              Sign out
            </Button>
          </div>
        ) : null}

        <div className="mt-auto p-3 bg-slate-50 border border-slate-200/60 rounded-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="size-3.5 text-slate-700" strokeWidth={1.5} />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Enterprise MVP</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Operational harness v0.1.0</p>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        {alerts.length > 0 && (
          <div
            className="mx-6 mt-4 border border-amber-200 bg-amber-50 text-amber-900 text-sm px-4 py-3 rounded-sm"
            data-testid="reminder-in-app-banner"
          >
            {alerts.length} follow-up reminder(s) due or overdue.{" "}
            <Link to="/leads" className="underline font-medium">
              Review in pipeline
            </Link>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
