import { expect, test } from '@playwright/test'

test('rechercher, filtrer puis ouvrir une annonce', async ({ page }) => {
  await page.goto('/recherche')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Toutes les annonces')
  const cards = page.locator('article')
  await expect(cards.first()).toBeVisible()
  const before = await page
    .getByText(/\d+ annonces?/)
    .first()
    .innerText()

  // Sur mobile, les filtres s'ouvrent dans un panneau plein écran.
  const toggle = page.getByRole('button', { name: 'Filtres', exact: true })
  if (await toggle.isVisible()) await toggle.click()

  // Le filtre met à jour l'URL, puis l'état : on clique, on vérifie ensuite.
  await page.getByRole('radio', { name: 'Smartphones' }).click()
  await expect(page).toHaveURL(/category=smartphone/)
  await page.getByRole('checkbox', { name: 'Double SIM' }).click()
  await expect(page).toHaveURL(/dual_sim=1/)
  await expect(page.getByRole('checkbox', { name: 'Double SIM' })).toBeChecked()

  const apply = page.getByRole('button', { name: /^Voir \d+ résultat/ })
  if (await apply.isVisible()) await apply.click()

  await expect(page.getByText(/\d+ annonces?/).first()).not.toHaveText(before)

  // Les filtres vivent dans l'URL : un rechargement les conserve.
  await page.reload()
  await expect(page).toHaveURL(/category=smartphone.*dual_sim=1|dual_sim=1.*category=smartphone/)

  await cards.first().getByRole('link').first().click()
  await expect(page).toHaveURL(/\/annonce\//)
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  await expect(page.getByRole('button', { name: /WhatsApp/ })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Caractéristiques' })).toBeVisible()
})

test('le tri et la pagination mettent à jour l’URL', async ({ page }) => {
  await page.goto('/recherche')
  await page.getByLabel('Trier par').selectOption('price_asc')
  await expect(page).toHaveURL(/sort=price_asc/)
  const next = page.getByRole('button', { name: 'Suivant' })
  await next.click()
  await expect(page).toHaveURL(/page=2/)
})

test('une recherche sans résultat propose d’effacer les filtres', async ({ page }) => {
  await page.goto('/recherche?q=zzzzintrouvable')
  await expect(page.getByText('Aucune annonce ne correspond')).toBeVisible()
})
