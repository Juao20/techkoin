import { expect, test, type Browser, type Page } from '@playwright/test'

// Needs demo data: `particulier` buys from the shop `boutique.pro` (shop Cotonou Tech).
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

/** A listing that accepts secure payment, is still for sale and belongs to a shop (never to the buyer). */
async function freeListing(page: Page, skip = 0, shop?: string) {
  const url = shop
    ? `/api/shops/${shop}/listings/?secure_payment=1&sort=recent`
    : '/api/listings/?secure_payment=1&seller_type=shop&sort=recent'
  const data = await (await page.request.get(url)).json()
  const active = data.results.filter((l: { status: string }) => l.status === 'active')
  return active[skip % active.length] as { id: number; slug: string; price_fcfa: number }
}
async function startOrder(buyer: Page, slug: string) {
  await buyer.goto(`/annonce/${slug}`)
  await buyer.getByRole('button', { name: 'Payer en sécurité' }).click()
  await expect(buyer).toHaveURL(/\/commande\/\d+/)
  await expect(buyer.getByText('Mode test')).toBeVisible()
  return new URL(buyer.url()).pathname
}

test('achat complet : paiement, remise, confirmation, versement', async ({ browser }, info) => {
  const viewport = info.project.use.viewport ?? undefined
  const buyer = await login(browser, 'particulier@demo.techkoin.test', viewport)
  const seller = await login(browser, 'boutique.pro@demo.techkoin.test', viewport)
  const listing = await freeListing(
    buyer,
    info.project.name === 'mobile-360' ? 0 : 1,
    'cotonou-tech',
  )

  const orderPath = await startOrder(buyer, listing.slug)
  await expect(buyer.getByText('Choisissez votre opérateur et payez')).toBeVisible()
  await buyer.getByRole('radio', { name: 'Moov Money' }).check()
  await buyer.getByLabel('Numéro Mobile Money').fill('01 97 12 34 56')
  await buyer.getByRole('button', { name: /^Payer / }).click()
  await expect(buyer.getByText('Payée, fonds en séquestre')).toBeVisible()
  await expect(buyer.getByText('Paiement reçu')).toBeVisible()

  // L'annonce est réservée pendant le séquestre.
  const reserved = await (await buyer.request.get(`/api/listings/${listing.slug}/`)).json()
  expect(reserved.status).toBe('reserved')

  // Le vendeur voit sa commission, puis signale la remise.
  await seller.goto(orderPath)
  await expect(seller.getByText('Commission TechKoin')).toBeVisible()
  await seller.getByRole('button', { name: 'J’ai remis l’appareil' }).click()
  await expect(seller.getByText('Appareil remis').first()).toBeVisible()

  // L'acheteur ne voit pas la commission et confirme la réception.
  await buyer.reload()
  await expect(buyer.getByText('Commission TechKoin')).toHaveCount(0)
  await buyer.getByRole('button', { name: 'Confirmer la réception' }).click()
  await expect(buyer.getByText('Fonds versés au vendeur').first()).toBeVisible()
  await expect(buyer.getByText('Achat terminé')).toBeVisible()

  const sold = await (await buyer.request.get(`/api/listings/${listing.slug}/`)).json()
  expect(sold.status).toBe('sold')

  // La commande apparaît dans l'espace compte des deux parties.
  await buyer.goto('/compte')
  await buyer.getByRole('tab', { name: 'Commandes' }).click()
  await expect(buyer.getByRole('link', { name: sold.title }).first()).toBeVisible()
  await buyer.context().close()
  await seller.context().close()
})

test('un paiement refusé annule la commande sans bloquer l’annonce', async ({ browser }, info) => {
  const buyer = await login(
    browser,
    'particulier@demo.techkoin.test',
    info.project.use.viewport ?? undefined,
  )
  const listing = await freeListing(buyer, 8 + Math.floor(Math.random() * 8))
  await startOrder(buyer, listing.slug)
  await buyer.getByLabel('Numéro Mobile Money').fill('01 97 12 34 00')
  await buyer.getByRole('button', { name: /^Payer / }).click()
  await expect(buyer.getByText('Annulée').first()).toBeVisible()
  await expect(buyer.getByText('Aucun argent n’a été prélevé')).toBeVisible()
  const after = await (await buyer.request.get(`/api/listings/${listing.slug}/`)).json()
  expect(after.status).toBe('active')
  await buyer.context().close()
})

test('litige : l’acheteur le signale, un modérateur rembourse', async ({ browser }, info) => {
  const viewport = info.project.use.viewport ?? undefined
  const buyer = await login(browser, 'particulier@demo.techkoin.test', viewport)
  const listing = await freeListing(buyer, 16 + Math.floor(Math.random() * 8))
  const orderPath = await startOrder(buyer, listing.slug)
  await buyer.getByLabel('Numéro Mobile Money').fill('01 97 12 34 56')
  await buyer.getByRole('button', { name: /^Payer / }).click()
  await expect(buyer.getByText('Payée, fonds en séquestre')).toBeVisible()

  await buyer.getByRole('button', { name: 'Ouvrir un litige' }).click()
  await buyer.getByLabel('Ce qui ne va pas').fill('Le vendeur ne vient pas au rendez-vous')
  await buyer.getByRole('button', { name: 'Envoyer le litige' }).click()
  await expect(buyer.getByText('Litige ouvert').first()).toBeVisible()
  await expect(buyer.getByText('Motif du litige')).toBeVisible()

  // Le modérateur tranche dans l'admin Django.
  const admin = await browser.newContext()
  const page = await admin.newPage()
  await page.goto('/admin/login/')
  await page
    .getByLabel(/Adresse e-mail|Nom d’utilisateur|Username/)
    .fill('admin@demo.techkoin.test')
  await page.getByLabel(/Mot de passe|Password/).fill(PASSWORD)
  await page.getByRole('button', { name: /Connexion|Log in/ }).click()
  const orderId = orderPath.split('/').pop()!
  await page.goto('/admin/payments/order/')
  await page.locator(`input[name="_selected_action"][value="${orderId}"]`).check()
  await page.locator('select[name="action"]').selectOption('refund_buyer')
  await page.getByRole('button', { name: /Envoyer|Go/ }).click()
  await admin.close()

  await buyer.reload()
  await expect(buyer.getByText('Remboursée').first()).toBeVisible()
  const after = await (await buyer.request.get(`/api/listings/${listing.slug}/`)).json()
  expect(after.status).toBe('active')
  await buyer.context().close()
})

test('le filtre « paiement sécurisé » et la commission avant publication', async ({ page }) => {
  await page.goto('/recherche?secure_payment=1')
  await expect(page.locator('article').first()).toBeVisible()
  const toggle = page.getByRole('button', { name: 'Filtres', exact: true })
  if (await toggle.isVisible()) await toggle.click()
  await expect(page.getByRole('checkbox', { name: 'Paiement sécurisé' })).toBeChecked()
  const body = await (await page.request.get('/api/payments/commission/?price=185000')).json()
  expect(body.commission_fcfa).toBe(5550)
})
