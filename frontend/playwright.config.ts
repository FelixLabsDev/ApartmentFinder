import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "cd .. && uv run uvicorn src.ui.api:app --port 8080",
      port: 8080,
      timeout: 30_000,
      reuseExistingServer: true,
    },
    {
      command: "npm run dev",
      port: 3000,
      timeout: 15_000,
      reuseExistingServer: true,
    },
  ],
});
