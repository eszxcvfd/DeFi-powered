// Locale switcher (US-047).
//
// Dropdown that lets the current user change their
// locale and timezone. Lives in the user menu; the
// admin surface for organization defaults lives in
// `OrganizationLocalePanel.tsx`.

import { useState } from "react";

import enUS from "@/locales/en-US.json";
import viVN from "@/locales/vi-VN.json";
import {
  isLocaleUnsupportedError,
  isTimezoneInvalidError,
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

export function LocaleSwitcher({ compact = false }: { compact?: boolean }) {
  const {
    locale,
    timezone,
    userLocale,
    userTimezone,
    setLocale,
    setTimezone,
    refresh,
  } = useLocale();
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const currentLocale: SupportedLocale = userLocale
    ? (userLocale as SupportedLocale)
    : locale;

  async function handleLocaleChange(value: string) {
    setError(null);
    setSaving(true);
    try {
      await setLocale(value as SupportedLocale);
    } catch (err) {
      if (isLocaleUnsupportedError(err)) {
        setError(t("settings.user_locale_unsupported", currentLocale));
      } else {
        setError(t("common.error", currentLocale));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleTimezoneChange(value: string) {
    setError(null);
    setSaving(true);
    try {
      await setTimezone(value);
    } catch (err) {
      if (isTimezoneInvalidError(err)) {
        setError(t("settings.user_locale_invalid_timezone", currentLocale));
      } else {
        setError(t("common.error", currentLocale));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={
        compact
          ? "flex flex-col gap-1 text-xs"
          : "flex flex-col gap-2 text-sm"
      }
      data-testid="locale-switcher"
    >
      <label className="flex flex-col gap-1">
        <span className="font-medium">{t("common.locale", currentLocale)}</span>
        <select
          value={currentLocale}
          onChange={(e) => handleLocaleChange(e.target.value)}
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
          value={userTimezone || timezone}
          onChange={(e) => handleTimezoneChange(e.target.value)}
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
      {error && (
        <span role="alert" className="text-red-600">
          {error}
        </span>
      )}
      <button
        type="button"
        onClick={() => void refresh()}
        className="text-xs underline self-start"
      >
        {t("common.retry", currentLocale)}
      </button>
    </div>
  );
}
