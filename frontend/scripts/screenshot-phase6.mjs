// Captures the phase 6 screens at 360 px and 1280 px into docs/screenshots/phase6/.
// Usage: npm run screenshots:phase6   (dev servers running, demo data loaded)
import { chromium } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const base = process.env.BASE_URL ?? 'http://localhost:5173'
const outDir = fileURLToPath(new URL('../../docs/screenshots/phase6/', import.meta.url))
const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
const python =
  process.env.PYTHON ?? fileURLToPath(new URL('../../.venv/Scripts/python.exe', import.meta.url))
const manage = (...args) =>
  execFileSync(python, ['manage.py', ...args], { cwd: backend, encoding: 'utf-8' })
mkdirSync(outDir, { recursive: true })

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

  // Facets and alert button on the results page, then the alert in the account.
  await page.goto(`${base}/connexion`)
  await page.getByLabel('E-mail ou téléphone').fill('particulier@demo.techkoin.test')
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)

  await page.goto(`${base}/recherche?q=iphone+13&price_max=${suffix === '360' ? 391000 : 392000}`)
  await page.getByRole('button', { name: 'Créer une alerte pour cette recherche' }).waitFor()
  if (width < 768) await page.getByRole('button', { name: 'Filtres', exact: true }).click()
  await page
    .getByText(/Smartphones \(\d+\)/)
    .first()
    .waitFor()
  await shot('resultats-facettes', false)
  if (width < 768) await page.getByRole('button', { name: /^Voir / }).click()
  await page.getByRole('button', { name: 'Créer une alerte pour cette recherche' }).click()
  await page.getByText('Alerte créée', { exact: false }).first().waitFor()

  manage(
    'shell',
    '-c',
    `from marketplace.models import Listing; from django.utils import timezone;` +
      `x = Listing.objects.filter(status='active', search_text__contains='iphone 13').exclude(seller__email='particulier@demo.techkoin.test').first();` +
      `Listing.objects.filter(pk=x.pk).update(price_fcfa=300000, published_at=timezone.now())`,
  )
  manage('send_alerts')

  await page.goto(`${base}/compte`)
  await page.getByRole('tab', { name: 'Alertes' }).click()
  await page.getByRole('button', { name: 'Mettre en pause' }).first().waitFor()
  await shot('compte-alertes')
  await page.getByRole('tab', { name: /Notifications/ }).click()
  await page
    .getByText(/nouvelle annonce/)
    .first()
    .waitFor()
  await shot('compte-notifications')

  await page.getByRole('tab', { name: 'Alertes' }).click()
  const remove = page.getByRole('listitem').filter({ hasText: 'iphone 13' }).getByRole('button', {
    name: 'Supprimer',
  })
  while (await remove.count()) {
    await remove.first().click()
    await page.waitForTimeout(300)
  }

  await page.goto(`${base}/cgu`)
  await page.getByRole('heading', { name: 'Conditions générales d’utilisation' }).waitFor()
  await shot('page-cgu')
  await context.close()
}
await browser.close()
