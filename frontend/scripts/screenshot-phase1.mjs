// Captures the main phase 1 pages at 360 px and 1280 px into docs/screenshots/phase1/.
// Usage: npm run screenshots:phase1   (dev servers running, demo data loaded)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase1/', import.meta.url))
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch()
for (const [suffix, width, height] of [
  ['360', 360, 780],
  ['1280', 1280, 900],
]) {
  const context = await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })
  const page = await context.newPage()
  const shot = async (name) => {
    await page.waitForLoadState('networkidle')
    await page.evaluate(() => document.fonts.ready)
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    console.log(`${name}-${suffix}: horizontal overflow = ${overflow}px`)
    await page.screenshot({ path: `${outDir}${name}-${suffix}.png`, fullPage: true })
  }

  await page.goto(`${base}/`)
  await shot('accueil')

  await page.goto(`${base}/recherche?category=laptop&sort=price_asc`)
  await shot('recherche')

  await page.goto(`${base}/recherche?category=smartphone`)
  await page.locator('article a').first().click()
  await page.waitForURL(/\/annonce\//)
  await shot('annonce')

  await page.goto(`${base}/boutique/cotonou-tech`)
  await shot('boutique')

  await page.goto(`${base}/connexion`)
  await page.getByLabel('E-mail ou téléphone').fill('particulier@demo.techkoin.test')
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)
  await shot('compte')

  await page.goto(`${base}/vendre`)
  await page.getByRole('button', { name: 'PC portables' }).click()
  await page.getByLabel('Modèle').fill('thinkpad')
  await page.getByRole('option').first().click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByRole('heading', { name: 'État', level: 2 }).waitFor()
  await shot('vendre-etat')

  await context.close()
}
await browser.close()
