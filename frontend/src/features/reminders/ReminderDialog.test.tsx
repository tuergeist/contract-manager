import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReminderDialog } from './ReminderDialog'

// --- i18n -------------------------------------------------------------------

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts ? `${key}|${JSON.stringify(opts)}` : key,
  }),
}))

// --- Apollo mock with per-mutation tracking --------------------------------

const createReminderFn = vi.fn()
const sendReminderFn = vi.fn()

vi.mock('@apollo/client', async () => {
  const actual = await vi.importActual<typeof import('@apollo/client')>(
    '@apollo/client',
  )
  return {
    ...actual,
    gql: (strings: TemplateStringsArray) => strings.join(''),
    useMutation: vi.fn((mutation: string) => {
      // Both mutation documents collapse to plain strings via our gql stub.
      // Pick the right vi.fn based on the operation name in the source.
      if (mutation.includes('CreatePaymentReminder')) {
        return [createReminderFn, { loading: false }]
      }
      if (mutation.includes('SendPaymentReminder')) {
        return [sendReminderFn, { loading: false }]
      }
      return [vi.fn(), { loading: false }]
    }),
  }
})

// --- Helpers ---------------------------------------------------------------

const baseDraft = {
  invoiceRecordId: 100,
  invoiceNumber: '2026-0001',
  stage: 1,
  language: 'de',
  title: '1. Mahnung',
  subject: '1. Mahnung Rechnung 2026-0001',
  bodyText: 'Bitte begleichen Sie den offenen Betrag.',
  feeAmount: '5.00',
  interestAmount: '12.34',
  interestRate: '9.0',
  interestDays: 30,
  overdueDays: 30,
}

function draftResponse(overrides: Partial<typeof baseDraft> = {}) {
  return {
    data: {
      createPaymentReminder: {
        success: true,
        error: null,
        draft: { ...baseDraft, ...overrides },
      },
    },
  }
}

describe('ReminderDialog', () => {
  beforeEach(() => {
    createReminderFn.mockReset()
    sendReminderFn.mockReset()
  })

  it('loads the draft when opened and pre-fills the form fields', async () => {
    createReminderFn.mockResolvedValue(draftResponse())

    render(
      <ReminderDialog open invoiceRecordId={100} onOpenChange={() => {}} />,
    )

    await waitFor(() =>
      expect(screen.getByTestId('reminder-title-input')).toBeInTheDocument(),
    )
    expect(createReminderFn).toHaveBeenCalledWith({
      variables: { invoiceRecordId: 100, stage: null },
    })
    expect(screen.getByTestId('reminder-title-input')).toHaveValue('1. Mahnung')
    expect(screen.getByTestId('reminder-subject-input')).toHaveValue(
      '1. Mahnung Rechnung 2026-0001',
    )
    expect(screen.getByTestId('reminder-body-input')).toHaveValue(
      'Bitte begleichen Sie den offenen Betrag.',
    )
  })

  it('shows an error state when the draft cannot be loaded', async () => {
    createReminderFn.mockResolvedValue({
      data: {
        createPaymentReminder: {
          success: false,
          error: 'Invoice is not eligible for dunning',
          draft: null,
        },
      },
    })

    render(
      <ReminderDialog open invoiceRecordId={100} onOpenChange={() => {}} />,
    )

    await waitFor(() =>
      expect(
        screen.getByText('Invoice is not eligible for dunning'),
      ).toBeInTheDocument(),
    )
    expect(screen.queryByTestId('reminder-title-input')).not.toBeInTheDocument()
  })

  it('sends the reminder with the edited fields and toggle values', async () => {
    createReminderFn.mockResolvedValue(draftResponse())
    sendReminderFn.mockResolvedValue({
      data: {
        sendPaymentReminder: {
          success: true,
          error: null,
          reminder: { id: 7, stage: 1, sentAt: '2026-05-22T08:00:00Z' },
        },
      },
    })

    const onSent = vi.fn()
    const onOpenChange = vi.fn()
    render(
      <ReminderDialog
        open
        invoiceRecordId={100}
        onOpenChange={onOpenChange}
        onSent={onSent}
      />,
    )

    await waitFor(() =>
      expect(screen.getByTestId('reminder-title-input')).toBeInTheDocument(),
    )

    const user = userEvent.setup()
    await user.clear(screen.getByTestId('reminder-body-input'))
    await user.type(screen.getByTestId('reminder-body-input'), 'Custom body')
    await user.click(screen.getByTestId('reminder-send-button'))

    await waitFor(() => expect(sendReminderFn).toHaveBeenCalledTimes(1))
    expect(sendReminderFn).toHaveBeenCalledWith({
      variables: expect.objectContaining({
        invoiceRecordId: 100,
        stage: 1,
        language: 'de',
        title: '1. Mahnung',
        subject: '1. Mahnung Rechnung 2026-0001',
        bodyText: 'Custom body',
        includeFee: true,
        includeInterest: true,
      }),
    })
    await waitFor(() => expect(onSent).toHaveBeenCalled())
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('surfaces a send error and keeps the dialog open', async () => {
    createReminderFn.mockResolvedValue(draftResponse())
    sendReminderFn.mockResolvedValue({
      data: {
        sendPaymentReminder: {
          success: false,
          error: 'Invoice is already paid',
          reminder: null,
        },
      },
    })

    const onOpenChange = vi.fn()
    render(
      <ReminderDialog
        open
        invoiceRecordId={100}
        onOpenChange={onOpenChange}
      />,
    )

    await waitFor(() =>
      expect(screen.getByTestId('reminder-send-button')).toBeInTheDocument(),
    )

    const user = userEvent.setup()
    await user.click(screen.getByTestId('reminder-send-button'))

    await waitFor(() =>
      expect(screen.getByText('Invoice is already paid')).toBeInTheDocument(),
    )
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
