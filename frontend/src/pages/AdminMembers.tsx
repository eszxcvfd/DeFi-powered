import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  UserPlus,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  KeyRound,
  Copy,
  X,
  AlertTriangle,
  Database,
} from "lucide-react";
import {
  changeMemberRole,
  createInvitation,
  disableMember,
  enableMember,
  listMembers,
  revokeInvitation,
  revokeMemberAccess,
} from "@/api/memberManagement";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type {
  InvitationView,
  MemberListResponse,
  MemberView,
} from "@/types/memberManagement";

const ROLES = [
  "admin",
  "compliance",
  "analyst",
  "sales_bd",
  "reviewer",
  "viewer",
] as const;

function stateBadge(state: string) {
  if (state === "active") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-emerald-50 text-emerald-700 border-emerald-200">
        <ShieldCheck className="size-3" /> active
      </span>
    );
  }
  if (state === "pending_invite" || state === "pending") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-amber-50 text-amber-700 border-amber-200">
        <ShieldAlert className="size-3" /> pending
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono border bg-rose-50 text-rose-700 border-rose-200">
      <ShieldX className="size-3" /> {state}
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

export default function AdminMembers() {
  const [data, setData] = useState<MemberListResponse | null>(null);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>("analyst");
  const [error, setError] = useState<string | null>(null);
  const [issuedToken, setIssuedToken] = useState<{ email: string; token: string; url: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setData(await listMembers());
  }

  useEffect(() => {
    void refresh();
  }, []);

  const members = useMemo(() => data?.members ?? [], [data]);
  const invitations = useMemo(() => data?.invitations ?? [], [data]);

  async function handleInvite() {
    if (!email.trim()) {
      setError("Email is required");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await createInvitation({ email: email.trim().toLowerCase(), role });
      setIssuedToken({
        email: result.invitation.email,
        token: result.invite_token,
        url: result.invite_url ?? "",
      });
      setEmail("");
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRoleChange(member: MemberView, newRole: string) {
    if (member.role === newRole) return;
    setError(null);
    setBusy(true);
    try {
      await changeMemberRole(member.id, newRole);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable(member: MemberView) {
    setError(null);
    setBusy(true);
    try {
      await disableMember(member.id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleEnable(member: MemberView) {
    setError(null);
    setBusy(true);
    try {
      await enableMember(member.id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(member: MemberView) {
    const ok = window.confirm(`Revoke access for ${member.email}? Active sessions will be invalidated.`);
    if (!ok) return;
    setError(null);
    setBusy(true);
    try {
      await revokeMemberAccess(member.id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRevokeInvite(inv: InvitationView) {
    setError(null);
    setBusy(true);
    try {
      await revokeInvitation(inv.id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function copyToClipboard(value: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      void navigator.clipboard.writeText(value);
    }
  }

  return (
    <AppPageShell testId="admin-members">
      <AppPageHeader
        title="Member management"
        subtitle="Invite teammates, change roles, disable or revoke access. Manual invite handoff is explicit; email delivery is a follow-on story."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/connectors" className="underline text-slate-600" data-testid="nav-connectors">
              Connectors
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/browser-profiles" className="underline text-slate-600" data-testid="nav-browser-profiles">
              Browser profiles
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/audit-log" className="underline text-slate-600" data-testid="nav-audit-log">
              Audit log
            </Link>
            <KeyRound className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-4 space-y-6">
            <AppSection title="Invite teammate">
              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-semibold text-slate-700">Email</Label>
                  <Input
                    data-testid="invite-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teammate@example.com"
                    className="mt-1.5 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-sm font-semibold text-slate-700">Role</Label>
                  <select
                    data-testid="invite-role"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="mt-1.5 w-full h-9 rounded-sm border border-slate-200 bg-white px-2 text-sm"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {r}
                      </option>
                    ))}
                  </select>
                </div>
                <Button
                  type="button"
                  data-testid="invite-submit"
                  onClick={() => void handleInvite()}
                  disabled={busy}
                  className="w-full rounded-sm text-sm font-semibold h-10 flex items-center justify-center gap-1.5"
                >
                  <UserPlus className="size-4" strokeWidth={2.5} />
                  Create invitation
                </Button>
                <p
                  className="text-[11px] text-slate-500 leading-relaxed"
                  data-testid="invite-handoff-note"
                >
                  Email delivery is not yet wired. The invite token is shown once after
                  creation; copy and send it manually.
                </p>
              </div>
            </AppSection>

            {issuedToken ? (
              <AppSection title="Latest invitation token">
                <div className="space-y-2 text-xs font-mono" data-testid="invite-token-card">
                  <p className="text-slate-600">
                    Invite for <span className="font-semibold">{issuedToken.email}</span>
                  </p>
                  <div className="flex items-center gap-2">
                    <code
                      className="flex-1 p-2 bg-slate-50 border border-slate-200 rounded-sm break-all"
                      data-testid="invite-token-value"
                    >
                      {issuedToken.token}
                    </code>
                    <Button
                      variant="ghost"
                      data-testid="invite-token-copy"
                      className="text-xs border border-slate-200 h-9"
                      onClick={() => copyToClipboard(issuedToken.token)}
                    >
                      <Copy className="size-3" /> Copy
                    </Button>
                    <Button
                      variant="ghost"
                      data-testid="invite-token-dismiss"
                      className="text-xs border border-slate-200 h-9"
                      onClick={() => setIssuedToken(null)}
                    >
                      <X className="size-3" />
                    </Button>
                  </div>
                  {issuedToken.url ? (
                    <p className="text-slate-500 text-[11px]">
                      Acceptance path: <code className="bg-slate-50 border border-slate-200 px-1 py-0.5 rounded-sm">{issuedToken.url}</code>
                    </p>
                  ) : null}
                </div>
              </AppSection>
            ) : null}

            {error ? (
              <div
                className="border border-rose-200 bg-rose-50 text-rose-800 text-sm px-4 py-3 rounded-sm flex items-start gap-2"
                data-testid="members-error"
                role="alert"
              >
                <AlertTriangle className="size-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            ) : null}
          </div>

          <div className="xl:col-span-8 space-y-6">
            <AppSection title="Current members" className="flex flex-col">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-xs">
                    <th className="px-5 py-3 font-semibold">Member</th>
                    <th className="px-5 py-3 font-semibold">Role</th>
                    <th className="px-5 py-3 font-semibold">State</th>
                    <th className="px-5 py-3 font-semibold">Joined</th>
                    <th className="px-5 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {members.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/20 transition-colors" data-testid="member-row">
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        <div className="flex flex-col">
                          <span>{m.display_name || m.email}</span>
                          <span className="text-xs text-slate-400 font-mono font-normal mt-0.5">{m.email}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-slate-600" data-testid="member-role">
                        <select
                          data-testid="member-role-select"
                          value={m.role}
                          onChange={(e) => void handleRoleChange(m, e.target.value)}
                          disabled={busy}
                          className="font-mono text-xs uppercase bg-white border border-slate-200 rounded-sm px-2 py-1"
                        >
                          {[m.role, ...ROLES.filter((r) => r !== m.role)]
                            .filter((r, idx, arr) => arr.indexOf(r) === idx)
                            .map((r) => (
                              <option key={r} value={r}>
                                {r}
                              </option>
                            ))}
                        </select>
                      </td>
                      <td className="px-5 py-4" data-testid="member-state">
                        {stateBadge(m.state)}
                      </td>
                      <td className="px-5 py-4 text-slate-500 font-mono text-xs">
                        {formatTs(m.created_at)}
                      </td>
                      <td className="px-5 py-4 text-right space-x-1">
                        {m.state === "active" ? (
                          <Button
                            variant="ghost"
                            data-testid="member-disable"
                            className="text-[11px] h-7 border border-slate-200"
                            onClick={() => void handleDisable(m)}
                            disabled={busy}
                          >
                            Disable
                          </Button>
                        ) : null}
                        {m.state === "disabled" ? (
                          <Button
                            variant="ghost"
                            data-testid="member-enable"
                            className="text-[11px] h-7 border border-slate-200"
                            onClick={() => void handleEnable(m)}
                            disabled={busy}
                          >
                            Enable
                          </Button>
                        ) : null}
                        <Button
                          variant="ghost"
                          data-testid="member-revoke"
                          className="text-[11px] h-7 border border-rose-200 text-rose-700"
                          onClick={() => void handleRevoke(m)}
                          disabled={busy}
                        >
                          Revoke
                        </Button>
                      </td>
                    </tr>
                  ))}
                  {members.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-slate-400">
                        <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                        <span>No members yet.</span>
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </AppSection>

            <AppSection title="Pending invitations" className="flex flex-col">
              <table className="w-full text-sm text-left">
                <thead>
                  <tr className="bg-slate-50/50 border-b border-slate-200 text-slate-500 font-mono uppercase tracking-wider text-xs">
                    <th className="px-5 py-3 font-semibold">Email</th>
                    <th className="px-5 py-3 font-semibold">Role</th>
                    <th className="px-5 py-3 font-semibold">Invited by</th>
                    <th className="px-5 py-3 font-semibold">Expires</th>
                    <th className="px-5 py-3 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invitations.map((inv) => (
                    <tr
                      key={inv.id}
                      className="hover:bg-slate-50/20 transition-colors"
                      data-testid="invitation-row"
                    >
                      <td className="px-5 py-4 font-semibold text-slate-900" data-testid="invitation-email">
                        {inv.email}
                      </td>
                      <td className="px-5 py-4 text-slate-600 font-mono text-xs uppercase" data-testid="invitation-role">
                        {inv.role}
                      </td>
                      <td className="px-5 py-4 text-slate-500 text-xs">{inv.invited_by_email || "system"}</td>
                      <td className="px-5 py-4 text-slate-500 font-mono text-xs">
                        {formatTs(inv.expires_at)}
                      </td>
                      <td className="px-5 py-4 text-right">
                        {inv.state === "pending" ? (
                          <Button
                            variant="ghost"
                            data-testid="invitation-revoke"
                            className="text-[11px] h-7 border border-rose-200 text-rose-700"
                            onClick={() => void handleRevokeInvite(inv)}
                            disabled={busy}
                          >
                            Revoke invite
                          </Button>
                        ) : (
                          <span className="text-xs text-slate-400 font-mono">{inv.state}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {invitations.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-10 text-center text-slate-400">
                        <Database className="size-8 mx-auto text-slate-300 mb-2" strokeWidth={1.5} />
                        <span>No invitations yet.</span>
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </AppSection>
          </div>
        </div>
      </div>
    </AppPageShell>
  );
}
