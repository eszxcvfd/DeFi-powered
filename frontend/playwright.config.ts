import { defineConfig } from "@playwright/test";

const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:4173",
    extraHTTPHeaders: {
      "X-Creation-Source": "playwright",
      "X-Actor-Label": "e2e-runner",
    },
    launchOptions: chromiumExecutable
      ? { executablePath: chromiumExecutable }
      : undefined,
  },
  webServer: {
    command: "bash ../scripts/e2e-with-api.sh",
    port: 4173,
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});