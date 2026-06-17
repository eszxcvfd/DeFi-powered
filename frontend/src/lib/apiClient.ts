// Lightweight axios-like fetch shim for the frontend.
//
// The pre-existing US-045 calendar export module
// imports `apiClient` with an axios-shaped API
// (`apiClient.get`, `.post`, `.delete`,
// `.defaults.baseURL`). This shim re-implements
// that surface on top of the global `fetch` so
// the existing call sites keep working without
// adding a new dependency.
//
// The shim is intentionally minimal: it routes
// every request through `fetch`, forwards the
// session cookies (`credentials: "include"`),
// surfaces non-2xx responses as `ApiError`, and
// resolves with the parsed JSON body. A future
// story can replace this with a typed client
// behind the same shape.

export type ApiError = Error & {
  status: number;
  statusText: string;
  body: unknown;
};

class ApiErrorImpl extends Error implements ApiError {
  status: number;
  statusText: string;
  body: unknown;
  constructor(
    message: string,
    status: number,
    statusText: string,
    body: unknown,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.body = body;
  }
}

type RequestOptions = {
  params?: Record<string, unknown>;
  headers?: Record<string, string>;
};

type ApiClientShape = {
  defaults: { baseURL: string };
  get: <T>(path: string, options?: RequestOptions) => Promise<T>;
  post: <T>(path: string, body: unknown, options?: RequestOptions) => Promise<T>;
  patch: <T>(path: string, body: unknown, options?: RequestOptions) => Promise<T>;
  put: <T>(path: string, body: unknown, options?: RequestOptions) => Promise<T>;
  delete: <T>(path: string, options?: RequestOptions) => Promise<T>;
};

function buildUrl(
  baseURL: string,
  path: string,
  params?: Record<string, unknown>,
): string {
  const url = new URL(path, baseURL);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null) continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

async function request<T>(
  method: string,
  baseURL: string,
  path: string,
  body: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = buildUrl(baseURL, path, options.params);
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers || {}),
  };
  let payload: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    headers["Content-Type"] =
      headers["Content-Type"] || "application/json";
    payload =
      typeof body === "string" ? body : JSON.stringify(body);
  }
  const res = await fetch(url, {
    method,
    credentials: "include",
    headers,
    body: payload,
  });
  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  if (!res.ok) {
    const detail =
      (parsed &&
        typeof parsed === "object" &&
        "detail" in (parsed as Record<string, unknown>) &&
        typeof (parsed as Record<string, unknown>).detail === "string"
        ? (parsed as Record<string, string>).detail
        : res.statusText) || `HTTP ${res.status}`;
    throw new ApiErrorImpl(detail, res.status, res.statusText, parsed);
  }
  return parsed as T;
}

function makeClient(baseURL: string): ApiClientShape {
  return {
    defaults: { baseURL },
    get: <T>(path: string, options?: RequestOptions) =>
      request<T>("GET", baseURL, path, undefined, options),
    post: <T>(path: string, body: unknown, options?: RequestOptions) =>
      request<T>("POST", baseURL, path, body, options),
    patch: <T>(path: string, body: unknown, options?: RequestOptions) =>
      request<T>("PATCH", baseURL, path, body, options),
    put: <T>(path: string, body: unknown, options?: RequestOptions) =>
      request<T>("PUT", baseURL, path, body, options),
    delete: <T>(path: string, options?: RequestOptions) =>
      request<T>("DELETE", baseURL, path, undefined, options),
  };
}

export const apiClient: ApiClientShape = makeClient(
  typeof window !== "undefined" ? window.location.origin : "",
);

export type { ApiClientShape };
