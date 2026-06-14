import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createBrowserProfile,
  expireBrowserProfile,
  listBrowserProfiles,
  lockBrowserProfile,
  renewBrowserProfile,
  type BrowserProfileView,
} from "@/api/browserProfiles";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AdminBrowserProfiles() {
  const [items, setItems] = useState<BrowserProfileView[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setItems(await listBrowserProfiles());
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function create() {
    setBusy(true);
    try {
      await createBrowserProfile(name || `Profile ${Date.now()}`, 30);
      setName("");
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function act(fn: (id: string) => Promise<unknown>, id: string) {
    setBusy(true);
    try {
      await fn(id);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppPageShell testId="admin-browser-profiles">
      <AppPageHeader
        backTo="/admin/connectors"
        backLabel="Connectors"
        title="Browser profiles"
        subtitle="Governed lifecycle, consent, and session reuse (US-024)"
      />
      <div className={PAGE_CONTENT_CLASS}>
        <AppSection title="Create profile" testId="browser-profile-create">
          <div className="flex flex-wrap gap-2 items-end max-w-lg">
            <div className="flex-1 min-w-[200px]">
              <Label className="text-xs">Name</Label>
              <Input
                data-testid="browser-profile-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1"
              />
            </div>
            <Button
              type="button"
              data-testid="browser-profile-create-btn"
              disabled={busy}
              onClick={() => void create()}
            >
              Create
            </Button>
          </div>
        </AppSection>

        <AppSection title="Profiles" testId="browser-profile-list" className="mt-6">
          {items.length === 0 ? (
            <p className="text-sm text-slate-500">No profiles yet.</p>
          ) : (
            <ul className="divide-y divide-slate-100 border border-slate-200 rounded-sm">
              {items.map((p) => (
                <li
                  key={p.id}
                  className="p-4 text-sm flex flex-wrap gap-3 justify-between items-start"
                  data-testid="browser-profile-row"
                >
                  <div>
                    <p className="font-semibold text-slate-900">{p.name}</p>
                    <p className="text-xs font-mono text-slate-500 mt-1" data-testid="browser-profile-state">
                      {p.effective_state} · consent {p.consent_status}
                      {p.state_material_present ? " · state saved" : ""}
                    </p>
                    {!p.launch_eligible && (
                      <p className="text-xs text-amber-800 mt-1" data-testid="browser-profile-blocked">
                        Blocked: {p.launch_blocked_reasons.join(", ")}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={busy || p.lifecycle_state === "locked"}
                      data-testid="browser-profile-lock"
                      onClick={() => void act(lockBrowserProfile, p.id)}
                    >
                      Lock
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      data-testid="browser-profile-renew"
                      onClick={() => void act(renewBrowserProfile, p.id)}
                    >
                      Renew
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={busy}
                      data-testid="browser-profile-expire"
                      onClick={() => void act(expireBrowserProfile, p.id)}
                    >
                      Expire
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-slate-500 mt-4">
            <Link to="/admin/connectors" className="underline">
              Connectors
            </Link>{" "}
            · Sessions can pass <span className="font-mono">browser_profile_id</span> when launching.
          </p>
        </AppSection>
      </div>
    </AppPageShell>
  );
}