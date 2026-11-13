// Captures the phase 5 shop dashboard at 360 px and 1280 px into docs/screenshots/phase5/.
// Usage: npm run screenshots:phase5   (dev servers running, demo data seeded today)
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase5/', import.meta.url))
mkdirSync(outDir, { recursive: true })

async function signIn(page, email) {
  await page.goto(`${base}/connexion`)
  await page.getByLabel('E-mail ou téléphone').fill(email)
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)
}

const browser = await chromium.launch()
for (const [suffix, width, height] of [
  ['360', 360, 780],
  ['1280', 1280, 900],
]) {
  for (const [who, email, shots] of [
    [
      'pro',
      'boutique.pro@demo.techkoin.test',
      [
        ['vue-ensemble', '/pro', 'Vues et contacts par jour'],
        ['annonces', '/pro/annonces', 'Chiffres des 30 derniers jours'],
        ['radar', '/pro/analyse?module=radar', 'Radar de la demande'],
        ['prix', '/pro/analyse?module=prix', 'Conseiller prix'],
        ['stock-dormant', '/pro/analyse?module=dormant', 'Stock dormant'],
        ['discuter', '/pro/analyse?module=chat', 'Discuter avec vos chiffres'],
        ['abonnement', '/pro/abonnement', 'Historique'],
      ],
    ],
    [
      'gratuite',
      'boutique.gratuite@demo.techkoin.test',
      [
        ['apercu-radar', '/pro/analyse?module=radar', 'Radar de la demande'],
        ['rapport-verrouille', '/pro/analyse?module=rapport', 'Rapport hebdomadaire'],
      ],
    ],
  ]) {
    const context = await browser.newContext({ viewport: { width, height }, locale: 'fr-FR' })
    const page = await context.newPage()
    await signIn(page, email)
    for (const [name, path, marker] of shots) {
      await page.goto(`${base}${path}`)
      await page.getByText(marker, { exact: false }).first().waitFor()
      if (name === 'discuter') {
        await page
          .getByRole('button', { name: 'Combien de contacts sur les iPhone ce mois ?' })
          .click()
        await page.getByRole('status').first().waitFor()
      }
      await page.waitForLoadState('networkidle')
      await page.evaluate(() => document.fonts.ready)
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      )
      console.log(`${who}-${name}-${suffix}: horizontal overflow = ${overflow}px`)
      await page.screenshot({ path: `${outDir}${who}-${name}-${suffix}.png`, fullPage: true })
    }
    await context.close()
  }
}
await browser.close()
