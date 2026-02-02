import { test, expect } from '@playwright/test'

test.describe('Audit Log', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@test.local')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  })

  test('audit log page is accessible from navigation', async ({ page }) => {
    // Click on Audit Log in navigation
    await page.click('text=Audit Log')

    // Should navigate to audit log page
    await expect(page).toHaveURL('/audit-log')

    // Should show audit log page
    await expect(page.locator('[data-testid="audit-log-page"]')).toBeVisible()
  })

  test('audit log page shows entries', async ({ page }) => {
    // Go to audit log page
    await page.goto('/audit-log')

    // Should show audit log page
    await expect(page.locator('[data-testid="audit-log-page"]')).toBeVisible()

    // Should show audit log table or empty message
    const table = page.locator('[data-testid="audit-log-table-body"]')
    const emptyMessage = page.getByText('No audit log entries')

    // Either table or empty message should be visible
    const tableVisible = await table.isVisible().catch(() => false)
    const emptyVisible = await emptyMessage.isVisible().catch(() => false)

    expect(tableVisible || emptyVisible).toBe(true)
  })

  test('audit log page has filter controls', async ({ page }) => {
    // Go to audit log page
    await page.goto('/audit-log')

    // Should show filter dropdowns
    await expect(page.locator('select').first()).toBeVisible()
  })

  test('contract activity tab shows audit entries', async ({ page }) => {
    // Go to contracts page
    await page.goto('/contracts')

    // Wait for contracts table to load
    await page.waitForSelector('[data-testid="contracts-table-body"]')

    // Click on first contract
    const contractLink = page.locator('[data-testid^="contract-link-"]').first()
    const contractCount = await contractLink.count()

    if (contractCount > 0) {
      await contractLink.click()

      // Wait for contract detail page
      await expect(page).toHaveURL(/\/contracts\/\d+/)

      // Click on Activity tab
      await page.click('text=Activity')

      // Should show audit log table or empty message
      const table = page.locator('[data-testid="audit-log-table-body"]')
      const emptyMessage = page.getByText('No audit log entries')

      // Wait for content to load
      await page.waitForTimeout(1000)

      const tableVisible = await table.isVisible().catch(() => false)
      const emptyVisible = await emptyMessage.isVisible().catch(() => false)

      expect(tableVisible || emptyVisible).toBe(true)
    }
  })

  test('customer activity section shows audit entries', async ({ page }) => {
    // Go to customers page
    await page.goto('/customers')

    // Wait for customers table to load
    await page.waitForSelector('[data-testid="customers-table-body"]')

    // Click on first customer
    const customerLink = page.locator('[data-testid^="customer-link-"]').first()
    await customerLink.click()

    // Wait for customer detail page
    await expect(page).toHaveURL(/\/customers\/\d+/)

    // Should show activity section
    await expect(page.locator('[data-testid="customer-activity-section"]')).toBeVisible()

    // Should show audit log table or empty message
    const table = page.locator('[data-testid="audit-log-table-body"]')
    const emptyMessage = page.getByText('No audit log entries')

    // Wait for content to load
    await page.waitForTimeout(1000)

    const tableVisible = await table.isVisible().catch(() => false)
    const emptyVisible = await emptyMessage.isVisible().catch(() => false)

    expect(tableVisible || emptyVisible).toBe(true)
  })
})
