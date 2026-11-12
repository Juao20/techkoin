// Captures the dev-only styleguide at mobile (360 px) and desktop (1280 px) widths.
// Usage: npm run screenshots   (the Vite dev server must be running on :5173)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const out = new URL('../../docs/screenshots/', import.meta.url)
mkdirSync(out, { recursive: true })

const browser = await chromium.launch()
for (const [name, width, height] of [
  ['styleguide-360', 360, 800],
  ['styleguide-1280', 1280, 900],
]) {
  const page = await browser.newPage({ viewport: { width, height } })
  await page.goto(`${base}/_styleguide`, { waitUntil: 'networkidle' })
  await page.evaluate(() => document.fonts.ready)
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  console.log(`${name}: horizontal overflow = ${overflow}px`)
  await page.screenshot({ path: new URL(`${name}.png`, out).pathname.slice(1), fullPage: true })
  await page.close()
}
await browser.close()
