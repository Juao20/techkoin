import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

// Needs demo data. The scheduled job is run by hand, the way cron runs it every 15 minutes.
const backend = fileURLToPath(new URL('../../backend/', import.meta.url))
const python =
  process.env.PYTHON ?? fileURLToPath(new URL('../../.venv/Scripts/python.exe', import.meta.url))
const manage = (...args: string[]) =>
  execFileSync(python, ['manage.py', ...args], { cwd: backend, encoding: 'utf-8' })

test('une alerte prévient d’une nouvelle annonce par notification', async ({ page }, info) => {
  const budget = info.project.name === 'mobile-360' ? '412000' : '413000'
  await page.goto('/connexion')
  await page.getByLabel('E-mail ou téléphone').fill('particulier@demo.techkoin.test')
  await page.getByLabel('Mot de passe').fill('Demo2026!')
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)

  await page.goto(`/recherche?q=iphone+13&price_max=${budget}`)
  await page.getByRole('button', { name: 'Créer une alerte pour cette recherche' }).click()
  await expect(page.getByText('Alerte créée', { exact: false }).first()).toBeVisible()

  await page.goto('/compte')
  await page.getByRole('tab', { name: 'Alertes' }).click()
  const alert = page
    .getByRole('listitem')
    .filter({ hasText: `iphone 13 jusqu'à ${budget.slice(0, 3)} 000` })
  await expect(alert).toBeVisible()

  // Une annonce correspondante est publiée, puis le job planifié passe.
  manage(
    'shell',
    '-c',
    `from marketplace.models import Listing; from django.utils import timezone;` +
      `x = Listing.objects.filter(status='active', search_text__contains='iphone 13').exclude(seller__email='particulier@demo.techkoin.test').first();` +
      `Listing.objects.filter(pk=x.pk).update(price_fcfa=300000, published_at=timezone.now())`,
  )
  const out = manage('send_alerts')
  expect(out).toMatch(/notifiee/)

  await page.goto('/compte')
  await expect(page.getByRole('tab', { name: /Notifications \(\d+\)/ })).toBeVisible()
  await page.getByRole('tab', { name: /Notifications/ }).click()
  await expect(page.getByText(/nouvelle annonce/).first()).toBeVisible()

  await page.getByRole('tab', { name: 'Alertes' }).click()
  await alert.getByRole('button', { name: 'Supprimer' }).click()
  await expect(alert).toHaveCount(0)
})
