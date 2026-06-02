import { test, expect } from '@playwright/test'

/**
 * E2E coverage for the payment reminders (Mahnungen) feature.
 *
 * These tests verify UI surface and structural pieces that do not require
 * an overdue invoice to be present in the seeded test data:
 *
 *  - Dunning settings page (form, save flow)
 *  - Overdue column header on the invoice list (presence + sort interaction)
 *  - Sidebar search finds the new "Dunning" settings entry
 *  - Reminder list shows the empty state on a customer / contract detail page
 *
 * The full "create + send reminder" flow needs a mahnfähige Rechnung in the
 * fixture and is tracked as a follow-up.
 */

test.describe('Payment Reminders (Mahnungen)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login')
    await page.fill('input[type="email"]', 'admin@test.local')
    await page.fill('input[type="password"]', 'admin123')
    await page.click('button[type="submit"]')
    await expect(page).toHaveURL('/')
  })

  test.describe('Dunning settings', () => {
    test('settings page renders with all configurable fields', async ({
      page,
    }) => {
      await page.goto('/settings/accounting/dunning')

      await expect(page.getByTestId('dunning-settings')).toBeVisible()
      await expect(page.getByTestId('dunning-default-payment-term')).toBeVisible()
      await expect(
        page.getByTestId('dunning-overdue-red-threshold'),
      ).toBeVisible()
      await expect(
        page.getByTestId('dunning-mahnfaehig-threshold'),
      ).toBeVisible()
      await expect(page.getByTestId('dunning-interest-rate')).toBeVisible()
      // A fee input per stage (0–3).
      for (const stage of [0, 1, 2, 3]) {
        await expect(page.getByTestId(`dunning-fee-stage-${stage}`)).toBeVisible()
      }
      await expect(page.getByTestId('dunning-save-button')).toBeVisible()
    })

    test('changing a threshold and saving keeps the new value', async ({
      page,
    }) => {
      await page.goto('/settings/accounting/dunning')
      await expect(page.getByTestId('dunning-settings')).toBeVisible()

      const threshold = page.getByTestId('dunning-mahnfaehig-threshold')
      await threshold.fill('21')
      await page.getByTestId('dunning-save-button').click()

      // Reload to confirm the value persisted.
      await page.goto('/settings/accounting/dunning')
      await expect(page.getByTestId('dunning-mahnfaehig-threshold')).toHaveValue(
        '21',
      )
    })

    test('language toggle switches between DE and EN templates', async ({
      page,
    }) => {
      await page.goto('/settings/accounting/dunning')
      await expect(page.getByTestId('dunning-settings')).toBeVisible()

      // DE template editor visible by default.
      await expect(
        page.getByTestId('dunning-template-de-0'),
      ).toBeVisible()

      await page.getByTestId('dunning-lang-en').click()
      await expect(
        page.getByTestId('dunning-template-en-0'),
      ).toBeVisible()
    })
  })

  test.describe('Invoice list overdue column', () => {
    test('overdue column header is visible and clickable for sorting', async ({
      page,
    }) => {
      await page.goto('/invoices')
      const header = page.getByTestId('invoice-overdue-header')
      await expect(header).toBeVisible()
      // Sort interaction must not throw or navigate away.
      await header.click()
      await expect(page).toHaveURL(/\/invoices/)
      await expect(header).toBeVisible()
    })
  })

  test.describe('Sidebar search', () => {
    test('search finds the Dunning settings entry', async ({ page }) => {
      await page.goto('/')

      // The sidebar search input is a textbox-based control; rely on its
      // placeholder rather than text content so the test works for DE+EN.
      const searchInputs = page
        .locator('input[type="search"], input[placeholder]')
        .filter({ hasNot: page.locator('input[type="hidden"]') })
      // Pick the first search-like input on the chrome.
      const search = searchInputs.first()
      await search.click()
      await search.fill('Mahnwesen')

      // The result list should surface a link to the dunning settings page.
      const dunningLink = page.locator(
        'a[href="/settings/accounting/dunning"]',
      )
      await expect(dunningLink.first()).toBeVisible({ timeout: 5_000 })
    })
  })

  test.describe('Customer detail — reminders + payment term', () => {
    test('shows the payment term field and reminder section', async ({
      page,
    }) => {
      await page.goto('/customers')
      await page.waitForSelector('[data-testid="customers-table-body"]')

      const firstCustomerLink = page
        .locator('[data-testid^="customer-link-"]')
        .first()
      const count = await firstCustomerLink.count()
      test.skip(count === 0, 'No customer in seed data')

      await firstCustomerLink.click()
      await expect(
        page.locator('[data-testid="customer-detail-page"]'),
      ).toBeVisible()

      // Reminder list should render (empty state is fine — fixture has no
      // overdue invoices).
      const emptyOrList = page
        .getByTestId('reminder-list-empty')
        .or(page.getByTestId('reminder-list'))
      await expect(emptyOrList.first()).toBeVisible()
    })
  })

  test.describe('Full create + send reminder flow', () => {
    // Relies on the E2E fixture created by `setup_test_data`:
    //   invoice "E2E-OVERDUE-0001", 30 days overdue, customer
    //   "E2E Overdue Customer" with billing_emails set.
    const INVOICE_NUMBER = 'E2E-OVERDUE-0001'

    test('mahnen a fixture invoice and see the reminder on the invoice detail', async ({
      page,
    }) => {
      await page.goto('/invoices')

      // Locate the overdue fixture row.
      const invoiceCell = page.getByText(INVOICE_NUMBER).first()
      const visible = await invoiceCell
        .waitFor({ state: 'visible', timeout: 10_000 })
        .then(() => true)
        .catch(() => false)
      test.skip(
        !visible,
        `Fixture invoice ${INVOICE_NUMBER} missing — run setup_test_data`,
      )

      // The dunning action is only rendered for mahnfaehige invoices, so a
      // single matching button is enough to identify our fixture row.
      const dunButton = page.locator('[data-testid^="invoice-dun-"]').first()
      await expect(dunButton).toBeVisible()
      await dunButton.click()

      const dialog = page.getByTestId('reminder-dialog')
      await expect(dialog).toBeVisible()

      // Draft loaded → title input has been pre-filled.
      const titleInput = page.getByTestId('reminder-title-input')
      await expect(titleInput).not.toHaveValue('')

      // Verify the stage selector defaults to "0" (first mahnung) — fixture
      // wipes reminders on every setup_test_data run, so this is the first.
      await expect(page.getByTestId('reminder-stage-select')).toContainText(
        /Zahlungserinnerung|Payment reminder/,
      )

      // Send.
      await page.getByTestId('reminder-send-button').click()

      // On success the dialog closes itself.
      await expect(dialog).toBeHidden({ timeout: 10_000 })

      // Navigate to the invoice detail by clicking the invoice number link.
      await page.getByText(INVOICE_NUMBER).first().click()
      await expect(page).toHaveURL(/\/invoices\/\d+/)

      // The PaymentReminderList should now render at least one row.
      const list = page.getByTestId('reminder-list')
      await expect(list).toBeVisible({ timeout: 10_000 })
      await expect(list.locator('[data-testid^="reminder-row-"]')).toHaveCount(
        1,
        { timeout: 10_000 },
      )
    })
  })
})
