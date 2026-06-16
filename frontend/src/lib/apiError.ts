export function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (!detail || typeof detail !== "object") return fallback;
  const d = detail as Record<string, unknown>;
  if (Array.isArray(d.launch_errors) && d.launch_errors.length) {
    const code = String(d.launch_errors[0]);
    if (code === "source_not_found") {
      return "Source linked to this event is no longer in the registry (e.g. after reseed). Pick a browser connector below or add a browser/CloakBrowser source in Admin.";
    }
    if (code === "no_browser_source") {
      return "Could not provision browser connectors from source evidence (check event has a valid https URL).";
    }
    return `Launch blocked: ${d.launch_errors.join(", ")}`;
  }
  if (Array.isArray(d.policy_denied) && d.policy_denied.length) {
    return `Policy denied: ${d.policy_denied.join(", ")}`;
  }
  return JSON.stringify(detail);
}