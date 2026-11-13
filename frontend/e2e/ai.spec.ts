import { expect, test } from '@playwright/test'

// These tests run without GROQ_API_KEY: every feature must work on its fallback.

test('la recherche intelligente transforme une phrase en filtres modifiables', async ({ page }) => {
  await page.goto('/recherche')
  await page
    .getByLabel('Décrivez ce que vous cherchez')
    .fill('un pc pour coder pas trop cher vers Calavi, max 250k')
  await page.getByRole('button', { name: 'Chercher' }).click()
  await expect(page.getByText('Compris :')).toBeVisible()
  await expect(page).toHaveURL(/category=laptop/)
  await expect(page).toHaveURL(/price_max=250000/)
  await expect(page).toHaveURL(/usage(=|%3A)dev/)
  await expect(page).toHaveURL(/city=abomey-calavi/)

  await page.getByRole('button', { name: /Retirer max/ }).click()
  await expect(page).not.toHaveURL(/price_max/)
  await expect(page).toHaveURL(/category=laptop/)
})

test('une phrase saisie dans l’en-tête passe par la recherche intelligente', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('search').first().getByRole('searchbox').fill('samsung neuf max 150k')
  await page.keyboard.press('Enter')
  await expect(page.getByText('Compris :')).toBeVisible()
  await expect(page).toHaveURL(/price_max=150000/)
  await expect(page).toHaveURL(/brand=samsung/)
})

test('l’assistant répond depuis la fiche et propose de questionner le vendeur', async ({
  page,
  request,
}) => {
  const list = await (await request.get('/api/listings/?category=smartphone&sort=best_deal')).json()
  await page.goto(`/annonce/${list.results[0].slug}`)
  await page.getByRole('button', { name: 'La batterie tient combien ?' }).click()
  await expect(
    page.locator('li', { hasText: 'La batterie tient combien ?' }).first(),
  ).toContainText(/batterie|Score|pas indiquée/)

  await page.getByLabel('Votre question').fill('Est-ce qu’il supporte le Bluetooth 5.3 ?')
  await page.getByRole('button', { name: 'Demander' }).click()
  await expect(page.getByText(/Cette information n.est pas indiquée/)).toBeVisible()
  await expect(
    page.getByRole('button', { name: 'Poser la question au vendeur sur WhatsApp' }),
  ).toBeVisible()
})

test('la comparaison de trois annonces s’affiche en moins de 3 secondes', async ({
  page,
  request,
}) => {
  await page.goto('/recherche?category=smartphone')
  const cards = page.locator('article')
  await expect(cards.first()).toBeVisible()
  for (let i = 0; i < 3; i++) await cards.nth(i).getByLabel('Comparer').check()
  await page.getByRole('link', { name: 'Comparer' }).click()
  await expect(page).toHaveURL(/\/comparer\?ids=/)
  await expect(page.getByRole('heading', { name: 'Verdict TechKoin' })).toBeVisible()
  await expect(page.getByRole('table')).toBeVisible()
  await expect(page.getByText('Notre choix')).toBeVisible()

  // Hors cache (budget différent à chaque essai), temps de réponse de l'API.
  const ids = new URL(page.url()).searchParams.get('ids')!.split(',').map(Number)
  const started = Date.now()
  const res = await request.post('/api/ai/compare/', {
    data: { ids, usage: 'photo', budget: 100_000 + Math.floor(Math.random() * 1_000_000) },
  })
  expect(res.ok()).toBeTruthy()
  expect(Date.now() - started).toBeLessThan(3000)
})

test('la comparaison propose un usage et un budget', async ({ page, request }) => {
  const list = await (await request.get('/api/listings/?category=laptop')).json()
  const ids = list.results.slice(0, 2).map((l: { id: number }) => l.id)
  await page.goto(`/comparer?ids=${ids.join(',')}`)
  await expect(page.getByRole('heading', { name: 'Verdict TechKoin' })).toBeVisible()
  await page.getByLabel('Usage principal').selectOption('dev')
  await page.getByLabel(/Budget maximum/).fill('300000')
  await expect(page.getByRole('heading', { name: 'Verdict TechKoin' })).toBeVisible()
})

test('la dictée est masquée sans clé et la rédaction assistée fonctionne', async ({ page }) => {
  const stamp = Date.now()
  await page.goto('/inscription')
  await page.getByLabel('Prénom').fill('Assist')
  await page.getByLabel('E-mail').fill(`assist${stamp}@example.com`)
  await page.getByLabel('Téléphone').fill(`01${String(stamp).slice(-8)}`)
  await page.getByLabel('Mot de passe').fill('Motdepasse-2026')
  await page.getByRole('button', { name: 'Créer mon compte' }).click()
  await expect(page).toHaveURL(/\/vendre/)
  await expect(page.getByRole('button', { name: /Dicter/ })).toHaveCount(0)

  await page.getByRole('button', { name: 'Smartphones' }).click()
  await page.getByLabel('Modèle').fill('iphone 13')
  await page
    .getByRole('option', { name: /iPhone 13/ })
    .first()
    .click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await page.getByLabel('Stockage (Go)').fill('128')
  await page.getByRole('button', { name: 'Continuer' }).click()
  // The photos step does not block: the listing already exists, which is all the text needs.
  await expect(page.getByRole('heading', { name: 'Photos' })).toBeVisible()
  await page.getByRole('button', { name: 'Continuer' }).click()
  await expect(page.getByRole('heading', { name: 'Prix', level: 2 })).toBeVisible()
  await page.getByRole('button', { name: 'Rédiger la description à ma place' }).click()
  await expect(page.getByLabel(/Description/)).toHaveValue(/iPhone 13/, { timeout: 10_000 })
  await expect(page.getByLabel(/Description/)).toHaveValue(/128/)
})

for (const wish of [
  'pc pas cher',
  'pc gamer',
  'pc premium',
  'pc de bureau',
  'téléphone pas cher',
]) {
  test(`« ${wish} » trouve des annonces et explique ce qui a été compris`, async ({ page }) => {
    await page.goto('/recherche')
    await page.getByLabel('Décrivez ce que vous cherchez').fill(wish)
    await page.getByRole('button', { name: 'Chercher' }).click()
    await expect(page.getByText('Compris :')).toBeVisible()
    await expect(page.locator('article').first()).toBeVisible()
    const count = await page.getByLabel('Annonces', { exact: false }).count()
    expect(count).toBeGreaterThanOrEqual(0)
    await expect(page.getByText(/^[1-9]\d* annonces?$/)).toBeVisible()
  })
}
