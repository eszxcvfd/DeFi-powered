import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createWebhookSubscription,
  deleteWebhookSubscription,
  listWebhookChoices,
  listWebhookDeliveries,
  listWebhookSubscriptions,
  retryWebhookDelivery,
  rotateWebhookSecret,
  testWebhookSubscription,
  updateWebhookSubscription,
  type WebhookChoices,
  type WebhookDeliveryView,
  type WebhookEventTypeValue,
  type WebhookSubscriptionView,
} from "@/api/webhooks";
import { AppPageHeader } from "@/components/layout/AppPageHeader";
import { AppPageShell, PAGE_CONTENT_CLASS } from "@/components/layout/AppPageShell";
import { AppSection } from "@/components/layout/AppSection";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Key,
  Power,
  RefreshCcw,
  RotateCw,
  Send,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from "lucide-react";

export default function AdminWebhooks() {
  const [choices, setChoices] = useState<WebhookChoices | null>(null);
  const [subscriptions, setSubscriptions] = useState<
    WebhookSubscriptionView[]
  >([]);
  const [deliveries, setDeliveries] = useState<WebhookDeliveryView[]>([]);
  const [name, setName] = useState("");
  const [targetUrl, setTargetUrl] = useState("https://");
  const [eventTypes, setEventTypes] = useState<WebhookEventTypeValue[]>([
    "alert.fired",
  ]);
  const [message, setMessage] = useState<string | null>(null);
  const [recoveryReason, setRecoveryReason] = useState("");

  async function refresh() {
    try {
      const [c, s, d] = await Promise.all([
        listWebhookChoices(),
        listWebhookSubscriptions(),
        listWebhookDeliveries(),
      ]);
      setChoices(c);
      setSubscriptions(s.items);
      setDeliveries(d.items);
    } catch (err) {
      // The bounded surface may not be
      // reachable for the current role; the
      // panel renders an empty state in that
      // case.
      setChoices(null);
      setSubscriptions([]);
      setDeliveries([]);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      succeeded:
        "bg-emerald-50 text-emerald-700 border-emerald-200",
      failed: "bg-amber-50 text-amber-700 border-amber-200",
      dead_letter: "bg-rose-50 text-rose-700 border-rose-200",
      pending: "bg-slate-50 text-slate-600 border-slate-200",
      in_flight: "bg-blue-50 text-blue-700 border-blue-200",
      cancelled: "bg-slate-50 text-slate-500 border-slate-200",
    };
    const cls =
      colors[status] ??
      "bg-slate-50 text-slate-600 border-slate-200";
    return (
      <span
        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-sm text-xs font-mono border ${cls}`}
        data-testid={`webhook-status-${status}`}
      >
        {status}
      </span>
    );
  };

  const toggleEventType = (value: WebhookEventTypeValue) => {
    setEventTypes((prev) =>
      prev.includes(value)
        ? prev.filter((v) => v !== value)
        : [...prev, value]
    );
  };

  return (
    <AppPageShell testId="admin-webhooks">
      <AppPageHeader
        title="Webhook subscriptions"
        subtitle="Per-workspace outbound webhook delivery with HMAC signing, timestamp anti-replay, and bounded retry. Recovery is human-confirmed; evaluation cycles consume the US-046 health surface and the US-041 alert channel."
        meta={
          <span className="flex items-center gap-3 text-xs">
            <Link to="/admin/observability" className="underline text-slate-600" data-testid="nav-observability">
              Observability
            </Link>
            <span className="text-slate-300">|</span>
            <Link to="/admin/connectors" className="underline text-slate-600" data-testid="nav-connectors">
              Connectors
            </Link>
            <Settings2 className="size-4 text-slate-400 inline" />
          </span>
        }
      />
      <div className={PAGE_CONTENT_CLASS}>
        {message && (
          <div
            className="mb-4 p-3 border border-slate-200 rounded-sm bg-slate-50/40 text-xs font-mono text-slate-700"
            data-testid="webhook-message"
          >
            {message}
          </div>
        )}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          <div className="xl:col-span-5">
            <AppSection
              title="Subscriptions"
              description="Per-workspace webhook delivery. The signing secret is stored encrypted via the US-003 secret manager."
            >
              {subscriptions.length === 0 ? (
                <p
                  className="text-xs text-slate-400"
                  data-testid="webhook-subscriptions-empty"
                >
                  No subscriptions configured.
                </p>
              ) : (
                <div className="space-y-2">
                  {subscriptions.map((sub) => (
                    <div
                      key={sub.id}
                      className="border border-slate-200 rounded-sm p-3"
                      data-testid="webhook-subscription-row"
                    >
                      <div className="flex items-start justify-between gap-3 mb-2">
                        <div className="flex flex-col">
                          <span className="text-sm font-semibold text-slate-800">
                            {sub.name}
                          </span>
                          <span className="text-xs font-mono text-slate-500">
                            {sub.target_url}
                          </span>
                          <span className="text-xs text-slate-400 mt-1">
                            enabled={String(sub.enabled)} · secret_id=
                            {sub.secret_id.slice(0, 8)}
                          </span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {sub.event_types.map((et) => (
                              <span
                                key={et}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono bg-slate-100 text-slate-600 border border-slate-200"
                                data-testid={`webhook-event-type-${et}`}
                              >
                                {et}
                              </span>
                            ))}
                          </div>
                          {sub.last_rotated_at && (
                            <span className="text-[10px] text-slate-400 mt-1 font-mono">
                              rotated: {sub.last_rotated_at}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-col gap-1">
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-xs border border-slate-200"
                            data-testid="webhook-rotate-secret"
                            onClick={() =>
                              void rotateWebhookSecret(sub.id).then(
                                (updated) => {
                                  setMessage(
                                    `Secret rotated (v=${
                                      updated.last_rotated_at ?? "?"
                                    }).`
                                  );
                                  return refresh();
                                }
                              )
                            }
                          >
                            <RotateCw className="size-3.5" />
                            Rotate
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-xs border border-slate-200"
                            data-testid="webhook-test-send"
                            onClick={() =>
                              void testWebhookSubscription(sub.id)
                                .then((d) => {
                                  setMessage(
                                    `Test sent: status=${d.status} attempts=${d.attempt_count}.`
                                  );
                                  return refresh();
                                })
                                .catch((err) =>
                                  setMessage(
                                    err?.message ?? "Test failed"
                                  )
                                )
                            }
                          >
                            <Send className="size-3.5" />
                            Test
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-xs border border-slate-200"
                            data-testid="webhook-toggle-enabled"
                            onClick={() =>
                              void updateWebhookSubscription(sub.id, {
                                enabled: !sub.enabled,
                              }).then(() => refresh())
                            }
                          >
                            <Power className="size-3.5" />
                            {sub.enabled ? "Disable" : "Enable"}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            className="text-xs border border-slate-200"
                            data-testid="webhook-delete"
                            onClick={() => {
                              if (
                                typeof window !== "undefined" &&
                                !window.confirm(
                                  `Delete subscription ${sub.name}?`
                                )
                              ) {
                                return;
                              }
                              void deleteWebhookSubscription(sub.id).then(
                                () => refresh()
                              );
                            }}
                          >
                            <Trash2 className="size-3.5" />
                            Delete
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {choices && (
                <div className="mt-4 border border-slate-200 rounded-sm p-3 bg-slate-50/40 space-y-3">
                  <h5 className="text-xs font-semibold text-slate-700">
                    Create subscription
                  </h5>
                  <div>
                    <Label className="text-xs">Name</Label>
                    <Input
                      data-testid="webhook-create-name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. SIEM integration"
                      className="text-xs"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Target URL</Label>
                    <Input
                      data-testid="webhook-create-url"
                      value={targetUrl}
                      onChange={(e) => setTargetUrl(e.target.value)}
                      placeholder="https://siem.example.com/webhook"
                      className="text-xs font-mono"
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Event types</Label>
                    <div className="grid grid-cols-2 gap-1">
                      {choices.event_types.map((et) => (
                        <label
                          key={et.value}
                          className="flex items-center gap-2 text-xs"
                        >
                          <input
                            type="checkbox"
                            data-testid={`webhook-create-event-${et.value}`}
                            checked={eventTypes.includes(et.value)}
                            onChange={() => toggleEventType(et.value)}
                          />
                          <span className="font-mono">{et.value}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    data-testid="webhook-create"
                    className="text-xs"
                    onClick={() => {
                      if (!name.trim() || !targetUrl.trim()) {
                        setMessage("name and target_url are required");
                        return;
                      }
                      if (eventTypes.length === 0) {
                        setMessage("at least one event type is required");
                        return;
                      }
                      void createWebhookSubscription({
                        name,
                        target_url: targetUrl,
                        event_types: eventTypes,
                        enabled: true,
                      })
                        .then(() => {
                          setName("");
                          setTargetUrl("https://");
                          setEventTypes(["alert.fired"]);
                          setMessage("Subscription created.");
                          return refresh();
                        })
                        .catch((err) =>
                          setMessage(err?.message ?? "Failed")
                        );
                    }}
                  >
                    Create subscription
                  </Button>
                </div>
              )}
            </AppSection>
          </div>
          <div className="xl:col-span-7">
            <AppSection
              title="Delivery history"
              description="Bounded per-delivery history. Recovery is human-confirmed; failed and dead-letter deliveries can be retried."
            >
              {deliveries.length === 0 ? (
                <p
                  className="text-xs text-slate-400"
                  data-testid="webhook-deliveries-empty"
                >
                  No deliveries recorded.
                </p>
              ) : (
                <div className="space-y-2">
                  {deliveries.map((d) => (
                    <div
                      key={d.id}
                      className="border border-slate-200 rounded-sm p-3"
                      data-testid="webhook-delivery-row"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex flex-col">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-slate-700">
                              {d.event_type}
                            </span>
                            {getStatusBadge(d.status)}
                          </div>
                          <span className="text-[10px] text-slate-400 font-mono mt-1">
                            attempts={d.attempt_count} · sub=
                            {d.subscription_id.slice(0, 8)}
                            {d.last_response_code !== null &&
                              ` · status=${d.last_response_code}`}
                          </span>
                          {d.last_response_message && (
                            <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                              {d.last_response_message.slice(0, 80)}
                            </span>
                          )}
                          <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                            next={d.next_attempt_at ?? "-"}
                          </span>
                        </div>
                        {d.status === "failed" || d.status === "dead_letter" ? (
                          <div className="flex flex-col gap-1">
                            <Input
                              data-testid="webhook-retry-reason"
                              value={recoveryReason}
                              onChange={(e) =>
                                setRecoveryReason(e.target.value)
                              }
                              placeholder="Reason (required)"
                              className="text-xs w-40"
                            />
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              className="text-xs border border-slate-200"
                              data-testid="webhook-retry"
                              onClick={() => {
                                if (!recoveryReason.trim()) {
                                  setMessage("Reason required for retry");
                                  return;
                                }
                                void retryWebhookDelivery(d.id)
                                  .then(() => {
                                    setMessage("Retry queued.");
                                    setRecoveryReason("");
                                    return refresh();
                                  })
                                  .catch((err) =>
                                    setMessage(err?.message ?? "Failed")
                                  );
                              }}
                            >
                              <RefreshCcw className="size-3.5" />
                              Retry
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </AppSection>
          </div>
        </div>
        <div className="mt-6 text-[10px] text-slate-400 font-mono">
          <ShieldCheck className="size-3.5 inline mr-1" />
          HMAC-SHA256 + 300s replay window + bounded
          exponential backoff (max 6 attempts) + 24h
          window bound by EnvironmentMode.
          <ShieldAlert className="size-3.5 inline mx-1" />
          Private IP / metadata endpoint / SSRF refusal
          per NFR-SEC-006.
          <Key className="size-3.5 inline mx-1" />
          Signing secret stored encrypted via US-003
          SecretVault (Fernet).
        </div>
      </div>
    </AppPageShell>
  );
}
