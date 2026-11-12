// Captures the phase 2 screens at 360 px and 1280 px into docs/screenshots/phase2/.
// Usage: npm run screenshots:phase2   (dev servers running, demo data loaded)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase2/', import.meta.url))
mkdirSync(outDir, { recursive: true })

const listings = await (
  await fetch(`${base}/api/listings/?category=smartphone&sort=best_deal`)
).json()
const slug = listings.results[0].slug

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

  await page.goto(`${base}/annonce/${slug}`)
  await page.getByRole('heading', { name: 'Prix et usages' }).waitFor()
  await shot('fiche-estimation')

  await page.goto(`${base}/appareil-vole`)
  await shot('appareil-vole')

  await page.goto(`${base}/connexion`)
  await page.getByLabel('E-mail ou téléphone').fill('particulier@demo.techkoin.test')
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)

  await page.goto(`${base}/annonce/${slug}`)
  await page.getByRole('button', { name: /Signaler cette annonce/ }).click()
  await page.getByRole('radio', { name: /Arnaque/ }).click()
  await shot('signalement', false)

  await page.goto(`${base}/compte`)
  await page.getByRole('tab', { name: 'Vérification' }).click()
  await shot('verification')

  await page.goto(`${base}/vendre`)
  await page.getByRole('button', { name: 'Smartphones' }).click()
  await page.getByLabel('Modèle').fill('iphone 13')
  await page.getByRole('option').first().click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByLabel('Stockage (Go)').fill('128')
  await page.getByRole('button', { name: 'Continuer' }).click()
  const files = page.locator('input[type=file]')
  await files.first().waitFor({ state: 'attached' })
  await context.close()

  if (suffix === '1280') {
    const admin = await browser.newContext({ viewport: { width: 1280, height: 700 } })
    const p = await admin.newPage()
    await p.goto(`${base}/admin/login/`)
    await p.getByLabel(/Adresse e-mail|Nom d’utilisateur|Username/).fill('admin@demo.techkoin.test')
    await p.getByLabel(/Mot de passe|Password/).fill('Demo2026!')
    await p.getByRole('button', { name: /Connexion|Log in/ }).click()
    await p.goto(`${base}/admin/trust/moderationqueueitem/`)
    await p.screenshot({ path: `${outDir}moderation-1280.png` })
    await admin.close()
  }
}
await browser.close()
