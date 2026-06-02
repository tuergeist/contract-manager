import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { PaymentReminderList } from './PaymentReminderList'
import type { PaymentReminder } from './dunning'

// react-i18next mock: return the key plus serialised options so we can assert on it.
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts ? `${key}|${JSON.stringify(opts)}` : key,
  }),
}))

function makeReminder(overrides: Partial<PaymentReminder> = {}): PaymentReminder {
  return {
    id: 1,
    invoiceRecordId: 100,
    invoiceNumber: '2026-0001',
    customerId: 7,
    customerName: 'ACME',
    stage: 1,
    language: 'de',
    title: '1. Mahnung',
    subject: '1. Mahnung Rechnung 2026-0001',
    bodyText: 'Bitte begleichen Sie den offenen Betrag.',
    feeAmount: '5.00',
    interestAmount: '12.34',
    interestRateSnapshot: '9.00',
    interestDays: 30,
    pdfUrl: 'https://example.test/reminder.pdf',
    sentAt: '2026-05-20T10:15:00Z',
    sentTo: ['billing@acme.test'],
    createdAt: '2026-05-20T10:14:00Z',
    ...overrides,
  }
}

function renderWith(reminders: PaymentReminder[], showInvoice = false) {
  return render(
    <MemoryRouter>
      <PaymentReminderList reminders={reminders} showInvoice={showInvoice} />
    </MemoryRouter>,
  )
}

describe('PaymentReminderList', () => {
  it('shows the empty state when there are no reminders', () => {
    renderWith([])
    expect(screen.getByTestId('reminder-list-empty')).toBeInTheDocument()
    expect(screen.queryByTestId('reminder-list')).not.toBeInTheDocument()
  })

  it('renders a reminder row with stage label, title, sent timestamp and PDF link', () => {
    renderWith([makeReminder()])

    const row = screen.getByTestId('reminder-row-1')
    expect(within(row).getByText('reminders.stage.1')).toBeInTheDocument()
    expect(within(row).getByText('1. Mahnung')).toBeInTheDocument()
    expect(screen.getByTestId('reminder-pdf-1')).toHaveAttribute(
      'href',
      'https://example.test/reminder.pdf',
    )
    // sent timestamp present (exact format is locale-dependent — just assert non-empty)
    const ts = screen.getByTestId('reminder-sent-at-1').textContent ?? ''
    expect(ts.length).toBeGreaterThan(0)
    expect(ts).not.toEqual('reminders.notSent')
  })

  it('renders the not-sent placeholder when sentAt is null', () => {
    renderWith([makeReminder({ id: 2, sentAt: null })])
    expect(screen.getByTestId('reminder-sent-at-2')).toHaveTextContent(
      'reminders.notSent',
    )
  })

  it('omits the PDF link when there is no pdfUrl', () => {
    renderWith([makeReminder({ id: 3, pdfUrl: null })])
    expect(screen.queryByTestId('reminder-pdf-3')).not.toBeInTheDocument()
  })

  it('shows an invoice link only when showInvoice is true', () => {
    const { rerender } = renderWith([makeReminder({ id: 4 })])
    expect(screen.queryByRole('link', { name: /2026-0001/ })).not.toBeInTheDocument()

    rerender(
      <MemoryRouter>
        <PaymentReminderList reminders={[makeReminder({ id: 4 })]} showInvoice />
      </MemoryRouter>,
    )
    const invoiceLink = screen.getByRole('link', { name: '2026-0001' })
    expect(invoiceLink).toHaveAttribute('href', '/invoices/100')
  })

  it('sorts reminders by sentAt descending (newest first)', () => {
    const reminders = [
      makeReminder({ id: 11, sentAt: '2026-04-01T08:00:00Z' }),
      makeReminder({ id: 12, sentAt: '2026-05-15T09:00:00Z' }),
      makeReminder({ id: 13, sentAt: '2026-03-20T07:00:00Z' }),
    ]
    renderWith(reminders)

    const rows = screen.getAllByTestId(/^reminder-row-\d+$/)
    const ids = rows.map((row) => row.getAttribute('data-testid'))
    expect(ids).toEqual([
      'reminder-row-12',
      'reminder-row-11',
      'reminder-row-13',
    ])
  })
})
