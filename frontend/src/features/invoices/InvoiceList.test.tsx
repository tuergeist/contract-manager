import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { InvoiceList } from './InvoiceList'

// --- Helpers to build mock data ---

function makeInvoice(i: number, overrides?: Partial<{ invoiceNumber: string }>) {
  return {
    id: String(i),
    invoiceNumber: overrides?.invoiceNumber ?? `INV-${String(i).padStart(4, '0')}`,
    invoiceDate: '2026-01-15',
    totalAmount: '100.00',
    currency: 'EUR',
    customerName: `Customer ${i}`,
    customerId: i,
    customerDisplayName: null,
    contractId: null,
    originalFilename: `invoice-${i}.pdf`,
    fileSize: 1024,
    pdfUrl: null,
    extractionStatus: 'done',
    extractionError: '',
    isPaid: false,
    paymentMatches: [],
    createdAt: '2026-01-15T00:00:00Z',
    createdByName: null,
    expectedFilename: '',
    receiverEmails: [],
    uploadStatus: 'uploaded',
    importBatchId: null,
  }
}

function makeGeneratedInvoice(i: number) {
  return {
    id: String(i),
    invoiceNumber: `GEN-${String(i).padStart(4, '0')}`,
    contractId: i,
    contractName: `Contract ${i}`,
    customerId: i,
    customerName: `Customer ${i}`,
    billingDate: '2026-01-15',
    totalGross: '200.00',
    status: 'generated',
    generatedAt: '2026-01-15T00:00:00Z',
    pdfUrl: null,
    isPaid: false,
    paymentMatches: [],
  }
}

// --- Track useQuery calls to return correct data per query ---

type QueryResult = {
  data: unknown
  loading: boolean
  refetch: ReturnType<typeof vi.fn>
  startPolling: ReturnType<typeof vi.fn>
  stopPolling: ReturnType<typeof vi.fn>
}

let queryResults: Map<string, QueryResult>

function setQueryData(querySubstring: string, data: unknown) {
  queryResults.set(querySubstring, {
    data,
    loading: false,
    refetch: vi.fn(),
    startPolling: vi.fn(),
    stopPolling: vi.fn(),
  })
}

function findQueryResult(queryStr: string): QueryResult {
  for (const [substring, result] of queryResults) {
    if (queryStr.includes(substring)) return result
  }
  return { data: null, loading: false, refetch: vi.fn(), startPolling: vi.fn(), stopPolling: vi.fn() }
}

// Mock Apollo
vi.mock('@apollo/client', async () => {
  const actual = await vi.importActual('@apollo/client')
  return {
    ...actual,
    gql: (strings: TemplateStringsArray) => strings.join(''),
    useQuery: vi.fn((query: string, _options?: unknown) => findQueryResult(query)),
    useMutation: vi.fn(() => [vi.fn(), { loading: false }]),
    useLazyQuery: vi.fn(() => [vi.fn(), { data: null, loading: false }]),
  }
})

// Mock auth
vi.mock('@/lib/auth', () => ({
  useAuth: vi.fn(),
}))

// Mock HelpVideoButton to avoid side-effects
vi.mock('@/components/HelpVideoButton', () => ({
  HelpVideoButton: () => null,
}))

import { useAuth } from '@/lib/auth'

function mockAuth(permissions: string[] = ['invoices.read', 'invoices.export']) {
  ;(useAuth as ReturnType<typeof vi.fn>).mockReturnValue({
    user: { id: 1, firstName: 'Test', lastName: 'User', email: 'test@test.local', tenantName: 'Test', permissions },
    hasPermission: (resource: string, action: string) =>
      permissions.includes(`${resource}.${action}`),
    isAuthenticated: true,
    isLoading: false,
    token: 'mock',
    login: vi.fn(),
    logout: vi.fn(),
    refetchUser: vi.fn(),
  })
}

function renderInvoiceList() {
  return render(
    <MemoryRouter>
      <InvoiceList />
    </MemoryRouter>
  )
}

// Helper: set up standard empty query results so the component doesn't crash
function setupEmptyQueries() {
  setQueryData('query Invoices', {
    invoices: { items: [], totalCount: 0, hasNextPage: false },
  })
  setQueryData('query InvoiceRecords', {
    invoiceRecords: { items: [], totalCount: 0, hasNextPage: false },
  })
  setQueryData('query ImportBatches', {
    importBatches: { items: [], totalCount: 0, hasNextPage: false },
  })
  setQueryData('query CustomerMatchSuggestions', { customerMatchSuggestions: [] })
  setQueryData('query SearchCustomers', { searchCustomers: [] })
  setQueryData('query SearchTransactions', { bankTransactions: { items: [] } })
}

describe('InvoiceList pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    queryResults = new Map()
    mockAuth()
  })

  it('renders page 1 imported invoices in ALL mode', () => {
    setupEmptyQueries()
    const items = Array.from({ length: 20 }, (_, i) => makeInvoice(i + 1))
    setQueryData('query Invoices', {
      invoices: { items, totalCount: 25, hasNextPage: true },
    })
    setQueryData('query InvoiceRecords', {
      invoiceRecords: { items: [], totalCount: 0, hasNextPage: false },
    })

    renderInvoiceList()

    expect(screen.getByText('INV-0001')).toBeInTheDocument()
    expect(screen.getByText('INV-0020')).toBeInTheDocument()
  })

  it('renders page 2 imported invoices in ALL mode (regression: double pagination)', async () => {
    setupEmptyQueries()
    // Simulate what the server returns for "ALL" mode: all imported invoices loaded at once
    // After the fix, ALL mode uses offset:0, limit:200, so all 25 items come back
    const allItems = Array.from({ length: 25 }, (_, i) => makeInvoice(i + 1))
    setQueryData('query Invoices', {
      invoices: { items: allItems, totalCount: 25, hasNextPage: false },
    })
    setQueryData('query InvoiceRecords', {
      invoiceRecords: { items: [], totalCount: 0, hasNextPage: false },
    })

    renderInvoiceList()

    // Page 1: should show first 20 items
    expect(screen.getByText('INV-0001')).toBeInTheDocument()
    expect(screen.getByText('INV-0020')).toBeInTheDocument()
    expect(screen.queryByText('INV-0021')).not.toBeInTheDocument()

    // Click next page button (the one with ChevronRight icon)
    const paginationButtons = screen.getAllByRole('button').filter(
      btn => btn.querySelector('svg.lucide-chevron-right')
    )
    expect(paginationButtons).toHaveLength(1)
    await userEvent.click(paginationButtons[0])

    // Page 2: should show items 21-25 (the remaining 5)
    expect(screen.getByText('INV-0021')).toBeInTheDocument()
    expect(screen.getByText('INV-0025')).toBeInTheDocument()
    // Page 1 items should not be shown
    expect(screen.queryByText('INV-0001')).not.toBeInTheDocument()
  })

  it('renders mixed imported + generated invoices across pages in ALL mode', async () => {
    setupEmptyQueries()
    const importedItems = Array.from({ length: 15 }, (_, i) => makeInvoice(i + 1))
    const generatedItems = Array.from({ length: 10 }, (_, i) => makeGeneratedInvoice(i + 1))

    setQueryData('query Invoices', {
      invoices: { items: importedItems, totalCount: 15, hasNextPage: false },
    })
    setQueryData('query InvoiceRecords', {
      invoiceRecords: { items: generatedItems, totalCount: 10, hasNextPage: false },
    })

    renderInvoiceList()

    // Total 25 items, page 1 should show 20
    // (exact mix depends on date sort, but all have same date so order is imported then generated)
    // At minimum, all 15 imported should be on page 1
    expect(screen.getByText('INV-0001')).toBeInTheDocument()
    expect(screen.getByText('INV-0015')).toBeInTheDocument()
    // First 5 generated should fill remaining slots on page 1
    expect(screen.getByText('GEN-0001')).toBeInTheDocument()
    expect(screen.getByText('GEN-0005')).toBeInTheDocument()
    // Items 21-25 (GEN-0006 to GEN-0010) should NOT be on page 1
    expect(screen.queryByText('GEN-0006')).not.toBeInTheDocument()

    // Click next page
    const paginationButtons = screen.getAllByRole('button').filter(
      btn => btn.querySelector('svg.lucide-chevron-right')
    )
    await userEvent.click(paginationButtons[0])

    // Page 2: remaining 5 generated invoices
    expect(screen.getByText('GEN-0006')).toBeInTheDocument()
    expect(screen.getByText('GEN-0010')).toBeInTheDocument()
    // Page 1 items should be gone
    expect(screen.queryByText('INV-0001')).not.toBeInTheDocument()
  })

  it('uses server pagination for IMPORTED filter mode', async () => {
    setupEmptyQueries()
    const page1Items = Array.from({ length: 20 }, (_, i) => makeInvoice(i + 1))
    setQueryData('query Invoices', {
      invoices: { items: page1Items, totalCount: 25, hasNextPage: true },
    })

    renderInvoiceList()

    // Switch to IMPORTED filter
    const sourceButtons = screen.getAllByRole('button')
    const importedButton = sourceButtons.find(btn => btn.textContent === 'invoices.import.sourceImported')
    expect(importedButton).toBeDefined()
    await userEvent.click(importedButton!)

    // Should show all 20 server-returned items (no client slicing)
    expect(screen.getByText('INV-0001')).toBeInTheDocument()
    expect(screen.getByText('INV-0020')).toBeInTheDocument()
  })
})
