// Captures the phase 4 payment screens at 360 px and 1280 px into docs/screenshots/phase4/.
// Usage: npm run screenshots:phase4   (dev servers running, demo data loaded, simulator provider)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase4/', import.meta.url))
mkdirSync(outDir, { recursive: true })

const browser = await chromium.launch()
let offset = 0
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

  await page.goto(`${base}/connexion`)
  await page.getByLabel('E-mail ou téléphone').fill('particulier@demo.techkoin.test')
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)

  const list = await (
    await page.request.get(`${base}/api/listings/?secure_payment=1&seller_type=shop&sort=recent`)
  ).json()
  const active = list.results.filter((l) => l.status === 'active')
  const slug = active[(30 + offset++) % active.length].slug

  await page.goto(`${base}/annonce/${slug}`)
  await page.getByRole('button', { name: 'Payer en sécurité' }).waitFor()
  await page.getByRole('button', { name: 'Payer en sécurité' }).scrollIntoViewIfNeeded()
  await shot('fiche-payer', false)

  await page.getByRole('button', { name: 'Payer en sécurité' }).click()
  await page.waitForURL(/\/commande\//)
  await page.getByLabel('Numéro Mobile Money').waitFor()
  await shot('commande-paiement')

  await page.getByLabel('Numéro Mobile Money').fill('01 97 12 34 56')
  await page.getByRole('button', { name: /^Payer / }).click()
  await page.getByText('Payée, fonds en séquestre').first().waitFor()
  await shot('commande-sequestre')

  await page.goto(`${base}/compte`)
  await page.getByRole('tab', { name: 'Commandes' }).click()
  await page.getByRole('link').filter({ hasText: /./ }).first().waitFor()
  await shot('compte-commandes')

  await context.close()
}
await browser.close()
