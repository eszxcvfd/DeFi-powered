import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Lock, ShieldCheck, Sparkles } from "lucide-react";
import { getBootstrapStatus } from "@/api/auth";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/components/AuthProvider";
import type { AuthBootstrapStatus } from "@/types/auth";

type FormState = {
  email: string;
  password: string;
  organizationId: string;
};

const DEFAULT_FORM: FormState = {
  email: "",
  password: "",
  organizationId: "",
};

export default function SignInPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useAuth();
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [status, setStatus] = useState<AuthBootstrapStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getBootstrapStatus()
      .then((s) => {
        if (cancelled) return;
        setStatus(s);
        setForm((f) => ({
          ...f,
          email: f.email || (s.has_users ? "" : s.default_email),
          organizationId: f.organizationId || s.default_organization_id,
        }));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signIn({
        email: form.email.trim(),
        password: form.password,
        organization_id: form.organizationId.trim() || undefined,
      });
      const redirect = (location.state as { from?: string } | null)?.from || "/";
      navigate(redirect, { replace: true });
    } catch (err) {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppPageShell testId="sign-in-page">
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-background)] py-10">
        <div className={PAGE_CONTENT_CLASS}>
          <AppPageHeader
            title="Sign in"
            subtitle="Use your LiveLead workspace email and password to sign in."
            meta={
              <span className="flex items-center gap-2 text-xs text-slate-500">
                <ShieldCheck className="size-4" strokeWidth={1.5} />
                Backend-enforced RBAC and tenant isolation
              </span>
            }
          />
          <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
            <div className="md:col-span-7">
              <AppSection title="Workspace credentials" testId="sign-in-form-section">
                <form
                  onSubmit={handleSubmit}
                  data-testid="sign-in-form"
                  className="space-y-3"
                >
                  <div>
                    <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                      Email
                    </Label>
                    <Input
                      data-testid="sign-in-email"
                      type="email"
                      value={form.email}
                      onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                      placeholder="you@example.com"
                      required
                      className="mt-1 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                      Password
                    </Label>
                    <Input
                      data-testid="sign-in-password"
                      type="password"
                      value={form.password}
                      onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                      placeholder="At least 12 characters"
                      required
                      className="mt-1 text-sm"
                    />
                  </div>
                  <div>
                    <Label className="text-[11px] font-mono uppercase tracking-wider text-slate-600">
                      Organization id (optional)
                    </Label>
                    <Input
                      data-testid="sign-in-organization"
                      value={form.organizationId}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, organizationId: e.target.value }))
                      }
                      placeholder="00000000-0000-4000-8000-000000000001"
                      className="mt-1 text-sm font-mono"
                    />
                  </div>
                  {error ? (
                    <p
                      data-testid="sign-in-error"
                      className="text-xs text-rose-700 border border-rose-200 bg-rose-50 px-3 py-2 rounded-sm"
                    >
                      {error}
                    </p>
                  ) : null}
                  <Button
                    type="submit"
                    disabled={loading}
                    data-testid="sign-in-submit"
                    className="w-full text-sm bg-slate-900 text-white hover:bg-slate-800"
                  >
                    <Lock className="size-4" />
                    {loading ? "Signing in…" : "Sign in"}
                  </Button>
                </form>
              </AppSection>
            </div>
            <div className="md:col-span-5 space-y-4">
              <AppSection
                title="Bootstrap hint"
                testId="sign-in-bootstrap-hint"
              >
                {status?.has_users === false ? (
                  <p className="text-xs text-slate-700" data-testid="bootstrap-empty">
                    <Sparkles className="inline size-3.5 mr-1 text-amber-500" />
                    A fresh workspace was detected. Sign in with{" "}
                    <span className="font-mono">{status.default_email}</span> using the
                    default owner password from your environment configuration.
                  </p>
                ) : (
                  <p className="text-xs text-slate-700">
                    Use the credentials that your LiveLead admin shared with you. Sign-in
                    failures are reported generically and recorded in the audit log.
                  </p>
                )}
              </AppSection>
              <AppSection title="Session" testId="sign-in-session-info">
                <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
                  <li>Backend enforces RBAC and tenant scope for every request.</li>
                  <li>Session cookies are HttpOnly, SameSite=Lax, and time-bounded.</li>
                  <li>All login and denial events are recorded in the audit log.</li>
                </ul>
              </AppSection>
            </div>
          </div>
        </div>
      </div>
    </AppPageShell>
  );
}
