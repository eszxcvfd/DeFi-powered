// i18n Provider (US-047).
//
// Loads the current-user locale and timezone from
// the API, exposes a `useLocale()` hook, and
// falls back to `en-US`/`UTC` when the API is
// unavailable. The provider is the single source
// of truth for the React surfaces.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_LOCALE,
  DEFAULT_TIMEZONE,
  fetchMyLocale,
  isSupportedLocale,
  updateMyLocale,
  type SupportedLocale,
  type UserLocaleView,
} from "@/api/i18n";

type ResolvedLocale = {
  locale: SupportedLocale;
  timezone: string;
  userLocale: string;
  userTimezone: string;
  localeSource: "user" | "organization" | "default";
  timezoneSource: "user" | "organization" | "default";
  loading: boolean;
  error: string | null;
};

type I18nContextValue = ResolvedLocale & {
  refresh: () => Promise<void>;
  setLocale: (locale: SupportedLocale) => Promise<void>;
  setTimezone: (timezone: string) => Promise<void>;
};

const I18nContext = createContext<I18nContextValue | null>(null);

const FALLBACK: ResolvedLocale = {
  locale: DEFAULT_LOCALE,
  timezone: DEFAULT_TIMEZONE,
  userLocale: "",
  userTimezone: "",
  localeSource: "default",
  timezoneSource: "default",
  loading: true,
  error: null,
};

export function I18nProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ResolvedLocale>(FALLBACK);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const view: UserLocaleView = await fetchMyLocale();
      const resolved: SupportedLocale = isSupportedLocale(view.resolved_locale)
        ? view.resolved_locale
        : DEFAULT_LOCALE;
      setState({
        locale: resolved,
        timezone: view.resolved_timezone || DEFAULT_TIMEZONE,
        userLocale: view.locale || "",
        userTimezone: view.timezone || "",
        localeSource: view.locale_source,
        timezoneSource: view.timezone_source,
        loading: false,
        error: null,
      });
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error:
          err instanceof Error ? err.message : "i18n load failed",
      }));
    }
  }, []);

  const setLocale = useCallback(
    async (locale: SupportedLocale) => {
      const view = await updateMyLocale({ locale });
      const resolved: SupportedLocale = isSupportedLocale(view.resolved_locale)
        ? view.resolved_locale
        : DEFAULT_LOCALE;
      setState({
        locale: resolved,
        timezone: view.resolved_timezone || DEFAULT_TIMEZONE,
        userLocale: view.locale || "",
        userTimezone: view.timezone || "",
        localeSource: view.locale_source,
        timezoneSource: view.timezone_source,
        loading: false,
        error: null,
      });
    },
    [],
  );

  const setTimezone = useCallback(async (timezone: string) => {
    const view = await updateMyLocale({ timezone });
    const resolved: SupportedLocale = isSupportedLocale(view.resolved_locale)
      ? view.resolved_locale
      : DEFAULT_LOCALE;
    setState({
      locale: resolved,
      timezone: view.resolved_timezone || DEFAULT_TIMEZONE,
      userLocale: view.locale || "",
      userTimezone: view.timezone || "",
      localeSource: view.locale_source,
      timezoneSource: view.timezone_source,
      loading: false,
      error: null,
    });
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<I18nContextValue>(
    () => ({ ...state, refresh, setLocale, setTimezone }),
    [state, refresh, setLocale, setTimezone],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useLocale(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    // Defensive fallback so a missing provider
    // does not crash the UI; surfaces still get
    // the global default.
    return {
      ...FALLBACK,
      loading: false,
      refresh: async () => {
        // no-op
      },
      setLocale: async () => {
        // no-op
      },
      setTimezone: async () => {
        // no-op
      },
    };
  }
  return ctx;
}

/**
 * Format a stored UTC datetime in the resolved
 * locale and timezone.
 *
 * The format is:
 *
 * - `vi-VN` — 24-hour `dd/MM/yyyy HH:mm`.
 * - `en-US` — 12-hour `MM/dd/yyyy, h:mm a`.
 */
export function formatDateTime(
  iso: string | null | undefined,
  locale: SupportedLocale,
  timezone: string,
): string {
  if (!iso) return "";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "";
  try {
    const formatter = new Intl.DateTimeFormat(
      locale === "vi-VN" ? "vi-VN" : "en-US",
      locale === "vi-VN"
        ? {
            timeZone: timezone || DEFAULT_TIMEZONE,
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          }
        : {
            timeZone: timezone || DEFAULT_TIMEZONE,
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "numeric",
            minute: "2-digit",
            hour12: true,
          },
    );
    return formatter.format(dt);
  } catch {
    return dt.toISOString();
  }
}

export function formatDate(
  iso: string | null | undefined,
  locale: SupportedLocale,
  timezone: string,
): string {
  const full = formatDateTime(iso, locale, timezone);
  if (!full) return "";
  if (locale === "vi-VN") {
    return full.split(" ")[0] || full.slice(0, 10);
  }
  return full.split(",")[0].trim();
}

export function formatTime(
  iso: string | null | undefined,
  locale: SupportedLocale,
  timezone: string,
): string {
  const full = formatDateTime(iso, locale, timezone);
  if (!full) return "";
  if (locale === "vi-VN") {
    return full.split(" ").slice(1).join(" ");
  }
  const parts = full.split(",");
  return (parts[1] || "").trim();
}
