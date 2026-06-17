// Localized datetime components (US-047).
//
// React components that consume the i18n provider
// and render a stored UTC datetime in the
// resolved locale and timezone. The components
// are the only way the React surfaces render a
// stored datetime.

import {
  formatDate,
  formatDateTime,
  formatTime,
  useLocale,
} from "@/lib/i18n";

type DatetimeProps = {
  iso: string | null | undefined;
  fallback?: string;
};

export function LocalizedDatetime({ iso, fallback = "" }: DatetimeProps) {
  const { locale, timezone } = useLocale();
  return <>{formatDateTime(iso, locale, timezone) || fallback}</>;
}

export function LocalizedDate({ iso, fallback = "" }: DatetimeProps) {
  const { locale, timezone } = useLocale();
  return <>{formatDate(iso, locale, timezone) || fallback}</>;
}

export function LocalizedTime({ iso, fallback = "" }: DatetimeProps) {
  const { locale, timezone } = useLocale();
  return <>{formatTime(iso, locale, timezone) || fallback}</>;
}
