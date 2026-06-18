import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { OfferDetail } from './OfferDetail'

// --- Mock data ---

function makeOffer(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    offerNumber: 'OFR-2026-0001',
    contractId: 10,
    contractName: 'Contract A',
    customerId: 5,
    customerName: 'Acme Corp',
    offerDate: '2026-06-01',
    validUntil: '2026-07-01',
    billingDate: '2026-06-01',
    periodStart: '2026-06-01',
    periodEnd: '2026-06-30',
    totalNet: '100.00',
    taxRate: '19.00',
    taxAmount: '19.00',
    totalGross: '119.00',
    status: 'draft',
    isLocked: false,
    createdAt: '2026-06-01T12:00:00Z',
    lineItemsSnapshot: [],
    pdfUrl: null,
    vatSentence: '',
    customerBillingEmails: [],
    emailSentAt: null,
    emailSentTo: [],
    emailMessageId: '',
    freeTextAfterItems: '',
    freeTextBeforeTerms: '',
    minimumTermMonths: null,
    noticePeriodMonths: null,
    clonedFromId: null,
    ...overrides,
  }
}

// --- Apollo mocks ---

type QueryResult = { data: unknown; loading: boolean; refetch: ReturnType<typeof vi.fn>; error?: unknown }
type MutationFn = ReturnType<typeof vi.fn>

let queryResults: Map<string, QueryResult>
let mutationSpies: Map<string, MutationFn>

function setQueryData(querySubstring: string, data: unknown) {
  queryResults.set(querySubstring, {
    data,
    loading: false,
    refetch: vi.fn().mockResolvedValue({ data }),
  })
}

function findQueryResult(queryStr: string): QueryResult {
  for (const [substring, result] of queryResults) {
    if (queryStr.includes(substring)) return result
  }
  return { data: null, loading: false, refetch: vi.fn() }
}

function findMutationSpy(mutationStr: string): MutationFn {
  for (const [substring, fn] of mutationSpies) {
    if (mutationStr.includes(substring)) return fn
  }
  // Default success response
  return vi.fn().mockResolvedValue({
    data: { updateOffer: { success: true, error: null, offer: { id: 1, status: 'draft', isLocked: false } } },
  })
}

vi.mock('@apollo/client', async () => {
  const actual = await vi.importActual('@apollo/client')
  return {
    ...actual,
    gql: (strings: TemplateStringsArray) => strings.join(''),
    useQuery: vi.fn((query: string) => findQueryResult(query)),
    useMutation: vi.fn((mutation: string) => [findMutationSpy(mutation), { loading: false }]),
  }
})

vi.mock('@/lib/auth', () => ({
  getToken: vi.fn(() => 'mock-token'),
}))

// react-markdown ships as ESM-only; stub it to a plain wrapper so jsdom can render
vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="md-rendered">{children}</div>,
}))

// SendOfferDialog touches GraphQL paths we don't exercise here
vi.mock('./SendOfferDialog', () => ({
  SendOfferDialog: () => null,
}))

// fetch for PDF blob
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  blob: () => Promise.resolve(new Blob(['%PDF-fake'])),
}) as unknown as typeof fetch

if (!global.URL.createObjectURL) {
  global.URL.createObjectURL = vi.fn(() => 'blob:mock')
  global.URL.revokeObjectURL = vi.fn()
}

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/offers/:id" element={<OfferDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  queryResults = new Map()
  mutationSpies = new Map()
})

describe('OfferDetail — save flow', () => {
  it('renders draft fields editable', () => {
    setQueryData('Offer', { offer: makeOffer() })
    renderWithRoute('/offers/1')
    expect(screen.getByText('OFR-2026-0001', { exact: false })).toBeInTheDocument()
    expect(screen.getByTestId('offer-free-text-after')).toBeInTheDocument()
    expect(screen.getByTestId('offer-free-text-before')).toBeInTheDocument()
  })

  it('Save button is disabled until a field changes', () => {
    setQueryData('Offer', { offer: makeOffer() })
    renderWithRoute('/offers/1')
    const saveBtn = screen.getByTestId('offer-save')
    expect(saveBtn).toBeDisabled()
  })

  it('typing into a free-text field enables the Save button and triggers updateOffer with the typed value', async () => {
    setQueryData('Offer', { offer: makeOffer() })
    const updateSpy = vi.fn().mockResolvedValue({
      data: { updateOffer: { success: true, error: null, offer: { id: 1, status: 'draft', isLocked: false } } },
    })
    mutationSpies.set('UpdateOffer', updateSpy)

    const user = userEvent.setup()
    renderWithRoute('/offers/1')

    const textarea = screen.getByTestId('offer-free-text-after') as HTMLTextAreaElement
    await user.type(textarea, 'hello world')

    const saveBtn = screen.getByTestId('offer-save')
    expect(saveBtn).not.toBeDisabled()

    await user.click(saveBtn)

    await waitFor(() => expect(updateSpy).toHaveBeenCalled())
    const call = updateSpy.mock.calls[0][0]
    expect(call.variables.id).toBe(1)
    expect(call.variables.input.freeTextAfterItems).toBe('hello world')
  })

  it('clears dirty state after a successful save', async () => {
    // Mock cache reflects the updated value after the save mutation +
    // refetch round-trip, so the derived isDirty flips back to false.
    const queryEntry: QueryResult = {
      data: { offer: makeOffer() },
      loading: false,
      refetch: vi.fn().mockImplementation(async () => {
        queryEntry.data = { offer: makeOffer({ freeTextAfterItems: 'x' }) }
        return { data: queryEntry.data }
      }),
    }
    queryResults.set('Offer', queryEntry)
    mutationSpies.set('UpdateOffer', vi.fn().mockImplementation(async () => {
      // Simulate the server-side write being visible immediately on next
      // read: bump the cached offer in lockstep with the resolver.
      queryEntry.data = { offer: makeOffer({ freeTextAfterItems: 'x' }) }
      return {
        data: { updateOffer: { success: true, error: null, offer: { id: 1, status: 'draft', isLocked: false } } },
      }
    }))

    const user = userEvent.setup()
    renderWithRoute('/offers/1')

    const textarea = screen.getByTestId('offer-free-text-after')
    await user.type(textarea, 'x')
    await user.click(screen.getByTestId('offer-save'))

    await waitFor(() => expect(screen.getByTestId('offer-save')).toBeDisabled())
    expect(screen.queryByText(/Ungespeicherte/i)).not.toBeInTheDocument()
  })

  it('typing in field B after field A was saved does NOT lose field B on the next refetch', async () => {
    // Repro of the 2.34.1 regression: race between blur-save of A and
    // user typing into B. State reset on refetch must not wipe B.
    const queryEntry: QueryResult = {
      data: { offer: makeOffer({ freeTextAfterItems: '' }) },
      loading: false,
      refetch: vi.fn().mockResolvedValue({}),
    }
    queryResults.set('Offer', queryEntry)
    mutationSpies.set('UpdateOffer', vi.fn().mockImplementation(async () => {
      queryEntry.data = { offer: makeOffer({ freeTextAfterItems: 'A' }) }
      return {
        data: { updateOffer: { success: true, error: null, offer: { id: 1, status: 'draft', isLocked: false } } },
      }
    }))

    const user = userEvent.setup()
    renderWithRoute('/offers/1')

    const fieldA = screen.getByTestId('offer-free-text-after') as HTMLTextAreaElement
    await user.type(fieldA, 'A')

    await user.click(screen.getByTestId('offer-save'))
    await waitFor(() => expect(screen.getByTestId('offer-save')).toBeDisabled())

    const fieldB = screen.getByTestId('offer-free-text-before') as HTMLTextAreaElement
    await user.type(fieldB, 'B')

    expect(fieldB.value).toBe('B')
    expect(screen.getByTestId('offer-save')).not.toBeDisabled()
  })

  it('shows a clear error toast when the server rejects the save', async () => {
    setQueryData('Offer', { offer: makeOffer() })
    mutationSpies.set('UpdateOffer', vi.fn().mockResolvedValue({
      data: { updateOffer: { success: false, error: 'Boom', isLockedError: false } },
    }))

    const user = userEvent.setup()
    renderWithRoute('/offers/1')

    await user.type(screen.getByTestId('offer-free-text-after'), 'x')
    await user.click(screen.getByTestId('offer-save'))

    await waitFor(() => expect(screen.getByText(/Boom/)).toBeInTheDocument())
    // Stays dirty so the user can retry
    expect(screen.getByTestId('offer-save')).not.toBeDisabled()
  })

  it('hides edit affordances on a locked offer', () => {
    setQueryData('Offer', { offer: makeOffer({ status: 'finalized', isLocked: true }) })
    renderWithRoute('/offers/1')
    expect(screen.queryByTestId('offer-free-text-after')).not.toBeInTheDocument()
    expect(screen.queryByTestId('offer-save')).not.toBeInTheDocument()
    expect(screen.getByTestId('offer-locked-banner')).toBeInTheDocument()
    expect(screen.getByTestId('offer-clone')).toBeInTheDocument()
  })
})
