import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const API = "http://127.0.0.1:8000";
const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
const CAMPAIGN_API = new RegExp(`^/campaigns/${UUID}(/sources|/discovery-jobs|/events)?$`, "i");
const DISCOVERY_JOB_API = new RegExp(`^/discovery-jobs/${UUID}(/cancel|/stream)?$`, "i");
const EVENT_ID_API = new RegExp(
  `^/events/${UUID}(/rescore|/audience/refresh|/engagement-plans|/engagement-tasks/${UUID}|/content/context|/content/drafts(?:/${UUID}(?:/submit-for-review)?)?)?$`,
  "i",
);
const CONTENT_DRAFT_API = new RegExp(`^/content/${UUID}(/approve|/reject|/export)?$`, "i");
const LEAD_ID_API = new RegExp(`^/leads(?:/${UUID})?$`, "i");
const ADMIN_CONNECTOR_ID = new RegExp(`^/admin/connectors/${UUID}$`, "i");

function wantsHtml(req: { headers?: Record<string, string> }) {
  const accept = (req.headers?.accept ?? "").toLowerCase();
  return accept.includes("text/html");
}

function campaignsProxyBypass(req: { method?: string; url?: string; headers?: Record<string, string> }) {
  const path = (req.url ?? "").split("?")[0];
  if (path === "/campaigns/new") return path;
  if (path === "/campaigns/runnable-sources") return null;
  if (CAMPAIGN_API.test(path)) {
    if (req.method === "GET" && wantsHtml(req)) return path;
    return null;
  }
  if (path === "/campaigns") {
    if (req.method === "GET" && wantsHtml(req)) return path;
    return null;
  }
  return path;
}

function discoveryProxyBypass(req: { method?: string; url?: string }) {
  const path = (req.url ?? "").split("?")[0];
  if (DISCOVERY_JOB_API.test(path)) return null;
  return path;
}

function eventsProxyBypass(req: { method?: string; url?: string; headers?: Record<string, string> }) {
  const path = (req.url ?? "").split("?")[0];
  if (EVENT_ID_API.test(path)) return null;
  if (path === "/events") {
    if (req.method === "GET" && wantsHtml(req)) return path;
    return null;
  }
  return path;
}

function adminProxyBypass(req: { method?: string; url?: string; headers?: Record<string, string> }) {
  const path = (req.url ?? "").split("?")[0];
  if (path === "/admin" || path === "/admin/connectors") {
    if (req.method === "GET" && wantsHtml(req)) return path;
    return null;
  }
  if (ADMIN_CONNECTOR_ID.test(path)) return null;
  return path;
}

const proxyConfig = {
  "/health": API,
  "/discovery-jobs": { target: API, bypass: discoveryProxyBypass },
  "/events": { target: API, bypass: eventsProxyBypass },
  "/admin": { target: API, bypass: adminProxyBypass },
  "/campaigns": { target: API, bypass: campaignsProxyBypass },
  "/content": API,
  "/reminders": API,
  "/leads": {
    target: API,
    bypass(req: { method?: string; url?: string; headers?: Record<string, string> }) {
      const path = (req.url ?? "").split("?")[0];
      if (LEAD_ID_API.test(path)) return null;
      if (path === "/leads" && req.method === "GET" && wantsHtml(req)) return path;
      return path;
    },
  },
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: { port: 5173, proxy: proxyConfig },
  preview: { port: 4173, proxy: proxyConfig },
});