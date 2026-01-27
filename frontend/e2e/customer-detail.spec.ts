import { test, expect } from '@playwright/test'

test.describe('Customer Detail', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@test.local')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  })

  test('customer name in customer list is clickable and navigates to detail page', async ({ page }) => {
    // Go to customers page
    await page.goto('/customers')

    // Wait for customers table to load
    await page.waitForSelector('[data-testid="customers-table-body"]')

    // Get first customer link using test ID pattern
    const firstCustomerRow = page.locator('[data-testid^="customer-row-"]').first()
    const customerLink = firstCustomerRow.locator('[data-testid^="customer-link-"]')
    const customerName = await customerLink.textContent()

    // Click on customer name
    await customerLink.click()

    // Should navigate to customer detail page
    await expect(page).toHaveURL(/\/customers\/\d+/)

    // Should show customer detail page
    await expect(page.locator('[data-testid="customer-detail-page"]')).toBeVisible()

    // Should show customer name in header
    await expect(page.locator('[data-testid="customer-name"]')).toContainText(customerName || '')
  })

  test('customer detail page shows customer information', async ({ page }) => {
    // Go to customers page
    await page.goto('/customers')

    // Wait for table and click first customer
    await page.waitForSelector('[data-testid="customers-table-body"]')
    await page.locator('[data-testid^="customer-link-"]').first().click()

    // Should show customer detail page
    await expect(page.locator('[data-testid="customer-detail-page"]')).toBeVisible()

    // Should show status badge
    await expect(page.locator('[data-testid="customer-status-badge"]')).toBeVisible()
  })

  test('customer detail page shows contracts section', async ({ page }) => {
    // Go to customers page
    await page.goto('/customers')

    // Wait for table and click first customer
    await page.waitForSelector('[data-testid="customers-table-body"]')
    await page.locator('[data-testid^="customer-link-"]').first().click()

    // Should show contracts section
    await expect(page.locator('[data-testid="customer-contracts-section"]')).toBeVisible()

    // Should show contracts count
    await expect(page.locator('[data-testid="customer-contracts-count"]')).toBeVisible()
  })

  test('customer name in contracts list links to customer detail', async ({ page }) => {
    // Go to contracts page
    await page.goto('/contracts')

    // Wait for contracts table to load
    await page.waitForSelector('[data-testid="contracts-table-body"]')

    // Check if there are any contracts
    const customerLinks = page.locator('[data-testid^="contract-customer-link-"]')
    const count = await customerLinks.count()

    if (count > 0) {
      // Get customer name from first contract row
      const customerLink = customerLinks.first()
      const customerName = await customerLink.textContent()

      // Click on customer name in contracts table
      await customerLink.click()

      // Should navigate to customer detail page
      await expect(page).toHaveURL(/\/customers\/\d+/)

      // Should show customer detail page
      await expect(page.locator('[data-testid="customer-detail-page"]')).toBeVisible()

      // Should show customer name
      await expect(page.locator('[data-testid="customer-name"]')).toContainText(customerName || '')
    }
  })

  test('back button on customer detail navigates to customers list', async ({ page }) => {
    // Go to customers page
    await page.goto('/customers')

    // Wait for table and click first customer
    await page.waitForSelector('[data-testid="customers-table-body"]')
    await page.locator('[data-testid^="customer-link-"]').first().click()

    // Wait for detail page
    await expect(page).toHaveURL(/\/customers\/\d+/)
    await expect(page.locator('[data-testid="customer-detail-page"]')).toBeVisible()

    // Click back button
    await page.locator('[data-testid="customer-back-button"]').click()

    // Should be back on customers list
    await expect(page).toHaveURL('/customers')
  })
})
