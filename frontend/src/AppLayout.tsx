import { LayoutDashboard, Radio, FileText, Kanban, Monitor, Settings, Sparkles } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { Button } from "@/components/ui/button";

const nav = [
  { label: "Dashboard", to: "/", icon: LayoutDashboard, end: true },
  { label: "Campaigns", to: "/campaigns", icon: Radio, end: false },
  { label: "Events", to: "/events", icon: FileText, end: true },
  { label: "Leads", to: "/leads", icon: Kanban, end: true },
  { label: "Browser session", to: "/browser", icon: Monitor, end: true },
  { label: "Admin", to: "/admin", icon: Settings, end: true },
];

export default function AppLayout() {
  return (
    <div className="min-h-screen flex bg-[var(--color-background)]">
      <aside className="w-60 border-r border-[var(--color-border)] bg-[var(--color-card)] p-5 flex flex-col gap-1.5">
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

        <div className="mt-auto p-3 bg-slate-50 border border-slate-200/60 rounded-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="size-3.5 text-slate-700" strokeWidth={1.5} />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Enterprise MVP</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Operational harness v0.1.0</p>
        </div>
      </aside>
      
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}