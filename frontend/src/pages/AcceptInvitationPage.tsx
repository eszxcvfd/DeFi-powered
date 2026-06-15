import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, ShieldCheck, AlertTriangle, ArrowRight } from "lucide-react";
import { acceptInvitation } from "@/api/memberManagement";
import { useAuth } from "@/components/AuthProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function AcceptInvitationPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [token, setToken] = useState<string>(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [acceptedAs, setAcceptedAs] = useState<{ role: string; email: string } | null>(null);

  useEffect(() => {
    setToken(params.get("token") ?? "");
  }, [params]);

  async function handleSubmit() {
    if (!token) {
      setError("Missing invitation token in the URL");
      return;
    }
    if (password.length < 12) {
      setError("Password must be at least 12 characters");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await acceptInvitation({
        token,
        password,
        display_name: displayName || undefined,
      });
      setAcceptedAs({ role: result.role, email: result.new_user ? "new user" : "linked user" });
      // Refresh the AuthProvider so the new session is picked up, then go home.
      try {
        await refresh();
      } catch {
        // Refresh is best-effort; the cookie was set on the response.
      }
      setTimeout(() => navigate("/", { replace: true }), 1200);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-[var(--color-background)] p-6"
      data-testid="accept-invitation-page"
    >
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-sm p-8 space-y-6">
        <div className="flex items-center gap-3">
          <div className="size-9 bg-slate-900 text-white flex items-center justify-center rounded-sm">
            <KeyRound className="size-4" />
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">LiveLead</p>
            <h1 className="text-lg font-bold tracking-tight text-slate-900">Accept invitation</h1>
          </div>
        </div>

        {acceptedAs ? (
          <div
            className="border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm px-4 py-3 rounded-sm flex items-start gap-2"
            data-testid="accept-success"
          >
            <ShieldCheck className="size-4 mt-0.5 shrink-0" />
            <div>
              <p className="font-semibold">Welcome — signed in as {acceptedAs.role}.</p>
              <p className="text-[11px] mt-0.5">Redirecting to the workspace…</p>
            </div>
          </div>
        ) : null}

        {error ? (
          <div
            className="border border-rose-200 bg-rose-50 text-rose-800 text-sm px-4 py-3 rounded-sm flex items-start gap-2"
            data-testid="accept-error"
            role="alert"
          >
            <AlertTriangle className="size-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <div className="space-y-4">
          <div>
            <Label className="text-sm font-semibold text-slate-700">Invitation token</Label>
            <Input
              data-testid="accept-token"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="paste the invite token"
              className="mt-1.5 text-sm font-mono"
            />
          </div>
          <div>
            <Label className="text-sm font-semibold text-slate-700">Display name (optional)</Label>
            <Input
              data-testid="accept-display-name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="mt-1.5 text-sm"
            />
          </div>
          <div>
            <Label className="text-sm font-semibold text-slate-700">Set a password</Label>
            <Input
              data-testid="accept-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="at least 12 characters"
              className="mt-1.5 text-sm"
            />
          </div>
          <Button
            type="button"
            data-testid="accept-submit"
            onClick={() => void handleSubmit()}
            disabled={busy || !token || password.length < 12}
            className="w-full rounded-sm text-sm font-semibold h-10 flex items-center justify-center gap-1.5"
          >
            Accept and sign in <ArrowRight className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
