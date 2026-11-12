import { expect, test } from '@playwright/test'
import { randomImei } from './helpers'

test('la fiche affiche l’estimation et les scores d’usage', async ({ page, request }) => {
  const res = await request.get('/api/listings/?category=smartphone&sort=best_deal')
  const data = (await res.json()) as { results: Array<{ slug: string; price_badge: string }> }
  const withBadge = data.results.find((l) => l.price_badge && l.price_badge !== 'unknown')
  const slug = (withBadge ?? data.results[0])!.slug
  await page.goto(`/annonce/${slug}`)
  await expect(page.getByRole('heading', { name: 'Prix et usages' })).toBeVisible()
  await expect(page.getByText(/Prix du marché/)).toBeVisible()
  expect(await page.getByRole('meter').count()).toBeGreaterThanOrEqual(5)
})

test('le filtre d’usage ne garde que les appareils bien notés', async ({ request }) => {
  const all = await (await request.get('/api/listings/?category=laptop')).json()
  const counts: number[] = []
  for (const usage of ['office', 'study', 'dev', 'gaming', 'creative', 'battery']) {
    const r = await (await request.get(`/api/listings/?category=laptop&usage=${usage}`)).json()
    expect(r.count).toBeLessThanOrEqual(all.count)
    counts.push(r.count)
  }
  expect(Math.max(...counts)).toBeGreaterThan(0)
})

test('un acheteur signale une annonce', async ({ page, request }) => {
  const list = await (await request.get('/api/listings/?category=smartphone')).json()
  const stamp = Date.now()
  await page.goto('/inscription')
  await page.getByLabel('Prénom').fill('Signal')
  await page.getByLabel('E-mail').fill(`signal${stamp}@example.com`)
  await page.getByLabel('Téléphone').fill(`01${String(stamp).slice(-8)}`)
  await page.getByLabel('Mot de passe').fill('Motdepasse-2026')
  await page.getByRole('button', { name: 'Créer mon compte' }).click()
  await expect(page).toHaveURL(/\/vendre/)

  // Trois signalements différents remettent une annonce en modération : on varie la cible.
  const target = list.results[Math.floor(Math.random() * list.results.length)]
  await page.goto(`/annonce/${target.slug}`)
  await page.getByRole('button', { name: /Signaler cette annonce/ }).click()
  await page.getByRole('radio', { name: /Arnaque/ }).click()
  await page.getByRole('button', { name: 'Envoyer le signalement' }).click()
  await expect(page.getByText(/signalement a bien été envoyé/)).toBeVisible()
})

test('un appareil volé peut être déclaré sans compte', async ({ page }) => {
  await page.goto('/appareil-vole')
  await page.getByLabel('IMEI ou numéro de série').fill(randomImei())
  await page.getByLabel('Que s’est-il passé ?').fill('Volé dans un taxi-moto à Cotonou.')
  await page.getByRole('button', { name: 'Envoyer la déclaration' }).click()
  await expect(page.getByText('Déclaration reçue')).toBeVisible()
})

test('les 5 annonces suspectes de la démo attendent en modération', async ({ page, request }) => {
  // Une annonce en modération n'est jamais visible du public.
  const all = await (await request.get('/api/listings/')).json()
  expect(all.count).toBeGreaterThan(100)

  await page.goto('/admin/login/')
  await page
    .getByLabel(/Adresse e-mail|Nom d’utilisateur|Username/)
    .fill('admin@demo.techkoin.test')
  await page.getByLabel(/Mot de passe|Password/).fill('Demo2026!')
  await page.getByRole('button', { name: /Connexion|Log in/ }).click()
  await page.goto('/admin/trust/moderationqueueitem/')
  const rows = page.locator('#result_list tbody tr')
  await expect(rows).toHaveCount(5)
  // La file est triée : l'appareil volé (score 100) est en tête.
  await expect(rows.first()).toContainText('100')
})
