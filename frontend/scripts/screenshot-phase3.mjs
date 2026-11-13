// Captures the phase 3 screens at 360 px and 1280 px into docs/screenshots/phase3/.
// Usage: npm run screenshots:phase3   (dev servers running, demo data loaded, no Groq key needed)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase3/', import.meta.url))
mkdirSync(outDir, { recursive: true })

const list = await (await fetch(`${base}/api/listings/?category=smartphone&sort=best_deal`)).json()
const slug = list.results[0].slug
const ids = list.results.slice(0, 3).map((l) => l.id)

const browser = await chromium.launch()
for (const [suffix, width, height] of [
  ['360', 360, 780],
  ['1280', 1280, 900],
]) {
  const context = await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })
  const page = await context.newPage()
  const shot = async (name, fullPage = true) => {
    await page.waitForLoadState('networkidle')
    await page.evaluate(() => document.fonts.ready)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    console.log(`${name}-${suffix}: horizontal overflow = ${overflow}px`)
    await page.screenshot({ path: `${outDir}${name}-${suffix}.png`, fullPage })
  }

  await page.goto(`${base}/recherche`)
  await page
    .getByLabel('Décrivez ce que vous cherchez')
    .fill('un pc pour coder pas trop cher vers Calavi, max 250k')
  await page.getByRole('button', { name: 'Chercher' }).click()
  await page.getByText('Compris :').waitFor()
  await shot('recherche-intelligente', false)

  await page.goto(`${base}/annonce/${slug}`)
  await page.getByRole('button', { name: 'La batterie tient combien ?' }).click()
  await page.getByRole('list').filter({ hasText: 'La batterie tient combien ?' }).first().waitFor()
  await page.getByLabel('Votre question').fill('Ça suffit pour Premiere Pro ?')
  await page.getByRole('button', { name: 'Demander' }).click()
  await page.getByText(/limitée sur un smartphone/).waitFor()
  await page
    .getByRole('heading', { name: 'Poser une question sur cette annonce' })
    .scrollIntoViewIfNeeded()
  await shot('assistant')

  await page.goto(`${base}/comparer?ids=${ids.join(',')}`)
  await page.getByRole('heading', { name: 'Verdict TechKoin' }).waitFor()
  await shot('comparaison')

  await context.close()
}
await browser.close()
