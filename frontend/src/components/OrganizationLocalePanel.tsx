// Organization locale panel (US-047).
//
// Admin surface for the organization default
// locale and timezone. Gated by owner/admin role;
// the user menu locale switcher is the
// non-admin path.

import { useEffect, useState } from "react";

import enUS from "@/locales/en-US.json";
import viVN from "@/locales/vi-VN.json";
import {
  fetchOrganizationLocale,
  isLocaleUnsupportedError,
  isTimezoneInvalidError,
  updateOrganizationLocale,
  type OrganizationLocaleView,
  type SupportedLocale,
} from "@/api/i18n";
import { useLocale } from "@/lib/i18n";

const COMMON_TIMEZONES: Array<{ value: string; label: string }> = [
  { value: "UTC", label: "UTC" },
  { value: "Asia/Ho_Chi_Minh", label: "Asia/Ho Chi Minh (UTC+7)" },
  { value: "Asia/Bangkok", label: "Asia/Bangkok (UTC+7)" },
  { value: "Asia/Singapore", label: "Asia/Singapore (UTC+8)" },
  { value: "Asia/Tokyo", label: "Asia/Tokyo (UTC+9)" },
  { value: "Asia/Shanghai", label: "Asia/Shanghai (UTC+8)" },
  { value: "Asia/Kolkata", label: "Asia/Kolkata (UTC+5:30)" },
  { value: "Europe/London", label: "Europe/London" },
  { value: "Europe/Berlin", label: "Europe/Berlin" },
  { value: "America/New_York", label: "America/New_York" },
  { value: "America/Los_Angeles", label: "America/Los_Angeles" },
];

const DICTIONARY: Record<SupportedLocale, Record<string, string>> = {
  "en-US": enUS as Record<string, string>,
  "vi-VN": viVN as Record<string, string>,
};

function t(key: string, locale: SupportedLocale): string {
  return DICTIONARY[locale]?.[key] ?? key;
}

export function OrganizationLocalePanel({
  organizationId,
}: {
  organizationId: string;
}) {
  const { locale: currentLocale } = useLocale();
  const [view, setView] = useState<OrganizationLocaleView | null>(null);
  const [draftLocale, setDraftLocale] = useState<SupportedLocale>("en-US");
  const [draftTimezone, setDraftTimezone] = useState<string>("UTC");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = await fetchOrganizationLocale(organizationId);
        if (cancelled) return;
        setView(result);
        setDraftLocale(
          (result.default_locale as SupportedLocale) || "en-US",
        );
        setDraftTimezone(result.default_timezone || "UTC");
      } catch (err) {
        if (!cancelled) {
          setError(t("common.error", currentLocale));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [organizationId, currentLocale]);

  async function handleSave() {
    setError(null);
    setSaved(false);
    setSaving(true);
    try {
      const result = await updateOrganizationLocale(organizationId, {
        default_locale: draftLocale,
        default_timezone: draftTimezone,
      });
      setView(result);
      setSaved(true);
    } catch (err) {
      if (isLocaleUnsupportedError(err)) {
        setError(t("settings.user_locale_unsupported", currentLocale));
      } else if (isTimezoneInvalidError(err)) {
        setError(t("settings.user_locale_invalid_timezone", currentLocale));
      } else {
        setError(t("common.error", currentLocale));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section
      className="flex flex-col gap-3 p-4 border rounded"
      data-testid="organization-locale-panel"
    >
      <header className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">
          {t("settings.organization_locale", currentLocale)}
        </h2>
        <p className="text-xs text-muted-foreground">
          {t("settings.organization_locale_help", currentLocale)}
        </p>
      </header>
      <div className="flex flex-col gap-2 text-sm">
        <label className="flex flex-col gap-1">
          <span className="font-medium">
            {t("common.locale", currentLocale)}
          </span>
          <select
            value={draftLocale}
            onChange={(e) =>
              setDraftLocale(e.target.value as SupportedLocale)
            }
            disabled={saving}
            className="border rounded px-2 py-1 bg-transparent"
          >
            <option value="vi-VN">
              {t("common.language_vi_vn", currentLocale)}
            </option>
            <option value="en-US">
              {t("common.language_en_us", currentLocale)}
            </option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-medium">
            {t("common.timezone", currentLocale)}
          </span>
          <select
            value={draftTimezone}
            onChange={(e) => setDraftTimezone(e.target.value)}
            disabled={saving}
            className="border rounded px-2 py-1 bg-transparent"
          >
            {COMMON_TIMEZONES.map((tz) => (
              <option key={tz.value} value={tz.value}>
                {tz.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {view && (
        <p className="text-xs text-muted-foreground">
          {t("common.locale", currentLocale)}: {view.default_locale} ·
          {" "}
          {t("common.timezone", currentLocale)}: {view.default_timezone}
        </p>
      )}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1 rounded bg-primary text-primary-foreground disabled:opacity-50"
        >
          {t("common.save", currentLocale)}
        </button>
        {saved && !error && (
          <span className="text-xs text-emerald-600">
            {t("settings.organization_locale_saved", currentLocale)}
          </span>
        )}
        {error && (
          <span role="alert" className="text-xs text-red-600">
            {error}
          </span>
        )}
      </div>
    </section>
  );
}
