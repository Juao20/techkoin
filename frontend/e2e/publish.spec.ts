import { expect, test, type Page } from '@playwright/test'

import { randomImei, randomPng } from './helpers'

async function addPhoto(page: Page, slot: string) {
  const li = page.locator('li', { hasText: slot }).first()
  const [chooser] = await Promise.all([
    page.waitForEvent('filechooser'),
    li.getByRole('button', { name: '+ Ajouter' }).click(),
  ])
  await chooser.setFiles({ name: 'photo.png', mimeType: 'image/png', buffer: randomPng() })
  await expect(li.locator('img')).toHaveCount(1)
}

test('un particulier publie une annonce complète en moins de 3 minutes', async ({ page }) => {
  const stamp = Date.now()
  const digits = String(stamp).slice(-8)

  // Inscription
  await page.goto('/inscription')
  await page.getByLabel('Prénom').fill('Essai')
  await page.getByLabel('E-mail').fill(`essai${stamp}@example.com`)
  await page.getByLabel('Téléphone').fill(`01${digits}`)
  await page.getByLabel('Mot de passe').fill('Motdepasse-2026')
  await page.getByRole('button', { name: 'Créer mon compte' }).click()
  await expect(page).toHaveURL(/\/vendre/)

  const started = Date.now()

  // 1. Appareil
  await page.getByRole('button', { name: 'Smartphones' }).click()
  await page.getByLabel('Modèle').fill('iphone 13')
  await page.getByRole('option').first().click()
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 2. État (note A proposée par défaut)
  await expect(page.getByRole('heading', { name: 'État', level: 2 })).toBeVisible()
  await page.getByLabel('Santé de la batterie (%)').fill('91')
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 3. Détails
  await expect(page.getByRole('heading', { name: 'Détails' })).toBeVisible()
  await page.getByLabel('Stockage (Go)').fill('128')
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 4. Photos
  await expect(page.getByRole('heading', { name: 'Photos' })).toBeVisible()
  await addPhoto(page, 'Face avant')
  await addPhoto(page, 'Face arrière')
  await addPhoto(page, 'Écran allumé')
  await addPhoto(page, 'Autre photo')
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 5. Prix
  await page.getByLabel('Prix (FCFA)').fill('250000')
  // L'estimation du marché s'affiche pendant la saisie du prix.
  await expect(page.getByText(/Prix du marché/)).toBeVisible()
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 6. Remise en main
  await page.getByLabel('Ville').selectOption({ label: 'Cotonou' })
  await page.getByLabel(/IMEI/).fill(randomImei())
  await page.getByLabel(/compte iCloud ou Google/).check()
  await page.getByRole('button', { name: 'Continuer' }).click()

  // 7. Publication
  await expect(page.getByText('À corriger avant de publier')).toHaveCount(0)
  await page.getByRole('button', { name: 'Publier mon annonce' }).click()
  await expect(page).toHaveURL(/\/annonce\//, { timeout: 20_000 })
  await expect(page.getByText('250 000 FCFA').first()).toBeVisible()

  expect(Date.now() - started).toBeLessThan(180_000)
})

test('un visiteur non connecté est renvoyé vers la connexion pour vendre', async ({ page }) => {
  await page.goto('/vendre')
  await expect(page).toHaveURL(/\/connexion/)
})
