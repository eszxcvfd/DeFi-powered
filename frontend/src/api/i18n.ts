// Internationalization and timezone API client (US-047).
//
// Talks to the bounded i18n and timezone surface on
// the backend. The client is the only place the
// React surfaces read the resolved locale and
// timezone.

export type SupportedLocale = "vi-VN" | "en-US";

export const DEFAULT_LOCALE: SupportedLocale = "en-US";
export const DEFAULT_TIMEZONE = "UTC";

export type UserLocaleView = {
  user_id: string;
  organization_id: string;
  locale: string;
  timezone: string;
  resolved_locale: string;
  resolved_timezone: string;
  locale_source: "user" | "organization" | "default";
  timezone_source: "user" | "organization" | "default";
};

export type OrganizationLocaleView = {
  organization_id: string;
  default_locale: string;
  default_timezone: string;
};

export type UserLocaleUpdateRequest = {
  locale?: string;
  timezone?: string;
};

export type OrganizationLocaleUpdateRequest = {
  default_locale?: string;
  default_timezone?: string;
};

export class I18nApiError extends Error {
  detail: string;
  status: number;
  constructor(detail: string, status: number) {
    super(`i18n api error: ${detail} (status=${status})`);
    this.detail = detail;
    this.status = status;
  }
}

async function readError(res: Response): Promise<I18nApiError> {
  let detail = "";
  try {
    const body = (await res.json()) as { detail?: string };
    detail = body.detail || res.statusText;
  } catch {
    detail = res.statusText;
  }
  return new I18nApiError(detail, res.status);
}

export async function fetchMyLocale(): Promise<UserLocaleView> {
  const r = await fetch("/me/locale", { method: "GET" });
  if (!r.ok) throw await readError(r);
  return r.json() as Promise<UserLocaleView>;
}

export async function updateMyLocale(
  payload: UserLocaleUpdateRequest,
): Promise<UserLocaleView> {
  const r = await fetch("/me/locale", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw await readError(r);
  return r.json() as Promise<UserLocaleView>;
}

export async function fetchOrganizationLocale(
  organizationId: string,
): Promise<OrganizationLocaleView> {
  const r = await fetch(
    `/admin/organizations/${organizationId}/locale`,
    { method: "GET" },
  );
  if (!r.ok) throw await readError(r);
  return r.json() as Promise<OrganizationLocaleView>;
}

export async function updateOrganizationLocale(
  organizationId: string,
  payload: OrganizationLocaleUpdateRequest,
): Promise<OrganizationLocaleView> {
  const r = await fetch(
    `/admin/organizations/${organizationId}/locale`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
  if (!r.ok) throw await readError(r);
  return r.json() as Promise<OrganizationLocaleView>;
}

export function isSupportedLocale(
  value: string | null | undefined,
): value is SupportedLocale {
  return value === "vi-VN" || value === "en-US";
}

export function isLocaleUnsupportedError(err: unknown): boolean {
  if (err instanceof I18nApiError) {
    return err.detail === "LOCALE_UNSUPPORTED";
  }
  return false;
}

export function isTimezoneInvalidError(err: unknown): boolean {
  if (err instanceof I18nApiError) {
    return err.detail === "TIMEZONE_INVALID";
  }
  return false;
}
