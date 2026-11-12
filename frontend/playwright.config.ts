import { defineConfig } from '@playwright/test'

/**
 * End-to-end tests run against the dev servers (Vite on :5173 proxying Django on :8000)
 * with demo data loaded: `python manage.py seed_catalog` then `python manage.py seed_demo`.
 * Start everything with `npm run dev` from the repository root, then `npm run e2e` here.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: process.env.BASE_URL ?? 'http://localhost:5173',
    locale: 'fr-FR',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'mobile-360', use: { viewport: { width: 360, height: 740 }, hasTouch: true } },
    { name: 'desktop-1280', use: { viewport: { width: 1280, height: 800 } } },
  ],
})
