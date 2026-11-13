import { expect, test, type Browser, type Page } from '@playwright/test'

// Needs demo data seeded today: `boutique.pro` (Cotonou Tech, Pro) and `boutique.gratuite` (Dantokpa Mobile, Free).
const PASSWORD = 'Demo2026!'

async function login(
  browser: Browser,
  email: string,
  viewport?: { width: number; height: number },
) {
  const context = await browser.newContext({ viewport, locale: 'fr-FR' })
  const page = await context.newPage()
  await page.goto('/connexion')
  await page.getByLabel('E-mail ou téléphone').fill(email)
  await page.getByLabel('Mot de passe').fill(PASSWORD)
  await page.getByRole('button', { name: 'Se connecter' }).click()
  await page.waitForURL(/\/compte/)
  return page
}

async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
  expect(overflow).toBeLessThanOrEqual(0)
}

test('boutique Pro : vue d’ensemble, puis radar cohérent avec les recherches simulées', async ({
  browser,
}, info) => {
  const page = await login(
    browser,
    'boutique.pro@demo.techkoin.test',
    info.project.use.viewport ?? undefined,
  )
  await page.goto('/pro')
  await expect(page.getByRole('heading', { name: 'Cotonou Tech' })).toBeVisible()
  await expect(page.getByText('Offre Pro', { exact: true })).toBeVisible()
  const stats = await (await page.request.get('/api/shop/stats/?period=30')).json()
  await expect(page.getByRole('list', { name: 'Chiffres clés' }).getByText('Vues')).toBeVisible()
  expect(stats.totals.views).toBeGreaterThan(0)
  await noHorizontalOverflow(page)

  await page.getByRole('link', { name: 'Analyse' }).click()
  await expect(page.getByRole('heading', { name: 'Radar de la demande' })).toBeVisible()
  const demand = await (await page.request.get('/api/insights/demand/?period=7')).json()
  expect(demand.preview).toBe(false)
  const mac = demand.rows.find(
    (r: { label: string; city: string | null }) => r.label === 'macbook m1',
  )
  expect(mac, 'la demande plantée par seed_demo apparaît dans le radar').toBeTruthy()
  expect(mac.searches).toBeGreaterThanOrEqual(10)
  // Ce que l'écran affiche est ce que l'API calcule à partir des événements.
  const row = page.getByRole('listitem').filter({ hasText: 'macbook m1' }).first()
  await expect(row).toContainText(String(mac.searches))
  await expect(row).toContainText('moins de 400')
  await expect(page.getByRole('heading', { name: 'À acheter en priorité' })).toBeVisible()
  await noHorizontalOverflow(page)
})

test('boutique Pro : prix, stock dormant, rapport, discussion, optimisation, concurrence', async ({
  browser,
}, info) => {
  const page = await login(
    browser,
    'boutique.pro@demo.techkoin.test',
    info.project.use.viewport ?? undefined,
  )
  await page.goto('/pro/analyse?module=prix')
  await expect(page.getByRole('heading', { name: 'Conseiller prix' })).toBeVisible()
  await expect(page.getByText(/Votre prix|cohérent|estimation/).first()).toBeVisible()

  await page.goto('/pro/analyse?module=dormant')
  await expect(page.getByRole('heading', { name: 'Stock dormant' })).toBeVisible()

  await page.goto('/pro/analyse?module=rapport')
  await page.getByRole('button', { name: 'Générer le rapport maintenant' }).click()
  await expect(page.getByRole('article', { name: 'Rapport' })).toContainText('Actions prioritaires')
  await noHorizontalOverflow(page)

  await page.goto('/pro/analyse?module=chat')
  await page.getByRole('button', { name: 'Quelles sont mes annonces les plus vues ?' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'En tête' })).toBeVisible()
  await page.getByLabel('Votre question').fill('Combien de vues cette semaine ?')
  await page.getByRole('button', { name: 'Envoyer' }).click()
  await expect(page.getByText(/vues cette semaine/).first()).toBeVisible()

  await page.goto('/pro/analyse?module=optimisation')
  await page.getByRole('checkbox').nth(1).click()
  await page.getByRole('button', { name: /Proposer de nouveaux textes/ }).click()
  await expect(page.getByText('Avant', { exact: true }).first()).toBeVisible()
  await expect(page.getByText('Après', { exact: true }).first()).toBeVisible()
  await noHorizontalOverflow(page)

  await page.goto('/pro/analyse?module=concurrence')
  await page.getByRole('combobox', { name: 'Mon annonce' }).click()
  await page.getByRole('option').first().click()
  await expect(
    page
      .getByRole('heading', { name: /Pourquoi un acheteur|Pas de concurrente/ })
      .or(page.getByText('Pas de concurrente proche')),
  ).toBeVisible()
})

test('boutique gratuite : aperçu réel et limité, fonctions Pro refusées par le serveur', async ({
  browser,
}, info) => {
  const page = await login(
    browser,
    'boutique.gratuite@demo.techkoin.test',
    info.project.use.viewport ?? undefined,
  )
  await page.goto('/pro')
  await expect(page.getByText('Offre gratuite')).toBeVisible()

  await page.goto('/pro/analyse?module=radar')
  await expect(page.getByRole('complementary', { name: 'Aperçu de l’offre Pro' })).toBeVisible()
  const demand = await (await page.request.get('/api/insights/demand/?period=7')).json()
  expect(demand.preview).toBe(true)
  expect(demand.rows).toHaveLength(1)
  expect(demand.hidden).toBeGreaterThan(0)
  expect(demand.recommendations).toBeUndefined()
  await expect(page.getByRole('list', { name: /Annonces concurrentes/ })).toHaveCount(0)

  for (const module of ['rapport', 'chat', 'optimisation', 'concurrence']) {
    await page.goto(`/pro/analyse?module=${module}`)
    await expect(page.getByText('Cette fonction fait partie de l’offre Pro.')).toBeVisible()
  }

  // Le front n'est pas la barrière : le serveur répond 403 à chaque point d'accès Pro.
  for (const [method, url] of [
    ['get', '/api/insights/reports/'],
    ['get', '/api/insights/competition/1/'],
  ] as const) {
    const res = await page.request[method](url)
    expect(res.status()).toBe(403)
    expect((await res.json()).code).toBe('forbidden')
  }
  await noHorizontalOverflow(page)
})

test('une nouvelle boutique passe en Pro avec le paiement sandbox', async ({ browser }, info) => {
  const context = await browser.newContext({
    viewport: info.project.use.viewport ?? undefined,
    locale: 'fr-FR',
  })
  const page = await context.newPage()
  const suffix = `${Date.now()}${info.project.name === 'mobile-360' ? 'm' : 'd'}`
  await page.goto('/inscription')
  await page.request.get('/api/auth/csrf/')
  const csrf = (await context.cookies()).find((c) => c.name === 'csrftoken')?.value ?? ''
  const registered = await page.request.post('/api/auth/register/', {
    headers: { 'X-CSRFToken': csrf },
    data: {
      email: `e2e-${suffix}@demo.techkoin.test`,
      phone: `01 96 ${suffix.slice(-6, -4)} ${suffix.slice(-4, -2)} ${suffix.slice(-2)}`.replace(
        /[a-z]/g,
        '1',
      ),
      password: PASSWORD,
      first_name: 'Essai',
      account_type: 'boutique',
      shop_name: `Boutique essai ${suffix}`,
      city: 'Cotonou',
    },
  })
  expect(registered.status(), await registered.text()).toBe(201)

  await page.goto('/pro/abonnement')
  await expect(page.getByText('Mode test')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Passez à l’offre Pro' })).toBeVisible()
  const refused = page.getByLabel('Numéro Mobile Money')
  await page.getByRole('radio', { name: 'MTN MoMo' }).check()
  await refused.fill('01 97 12 34 00')
  await page.getByRole('button', { name: /^Payer / }).click()
  await expect(page.getByText('Échouée')).toBeVisible()
  await expect(page.getByText('Offre gratuite')).toBeVisible()

  await refused.fill('01 97 12 34 56')
  await page.getByRole('button', { name: /^Payer / }).click()
  await expect(page.getByRole('heading', { name: 'Vous êtes sur l’offre Pro' })).toBeVisible()
  await expect(page.getByText('Offre Pro', { exact: true })).toBeVisible()

  // Le plan change tout de suite : les fonctions Pro répondent et les écrans se débloquent.
  expect((await page.request.get('/api/insights/reports/')).status()).toBe(200)
  await page.goto('/pro/analyse?module=rapport')
  await expect(page.getByRole('heading', { name: 'Rapport hebdomadaire' })).toBeVisible()
  await noHorizontalOverflow(page)
  await context.close()
})

test('les en-têtes de navigation du tableau de bord tiennent sur l’écran', async ({
  browser,
}, info) => {
  const page = await login(
    browser,
    'boutique.pro@demo.techkoin.test',
    info.project.use.viewport ?? undefined,
  )
  for (const path of ['/pro/annonces', '/pro/commandes', '/pro/parametres', '/pro/abonnement']) {
    await page.goto(path)
    await expect(page.getByRole('navigation', { name: 'Tableau de bord' })).toBeVisible()
    await noHorizontalOverflow(page)
  }
})
