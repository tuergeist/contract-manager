import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { InvoiceDetail } from './InvoiceDetail'

// --- Mock data ---

function makeInvoiceRecord() {
  return {
    id: 1,
    invoiceNumber: 'INV-2026-0001',
    contractId: 10,
    contractName: 'Contract A',
    customerId: 5,
    customerName: 'Acme Corp',
    billingDate: '2026-01-15',
    invoiceDate: '2026-01-15',
    periodStart: '2026-01-01',
    periodEnd: '2026-01-31',
    totalNet: '1000.00',
    taxRate: '19.00',
    taxAmount: '190.00',
    totalGross: '1190.00',
    status: 'finalized',
    lineItemsSnapshot: [],
    invoiceText: '',
    pdfUrl: null,
    isPaid: false,
    paymentMatches: [],
    voidReason: '',
    customerBillingEmails: [],
    emailSentAt: null,
    emailSentTo: [],
    emailMessageId: '',
  }
}

function makeImportedInvoice(overrides?: Partial<Record<string, unknown>>) {
  return {
    id: '42',
    invoiceNumber: 'IMP-2026-0001',
    invoiceDate: '2026-02-01',
    totalAmount: '500.00',
    currency: 'EUR',
    customerName: 'Test Customer',
    customerId: null,
    customerDisplayName: null,
    contractId: null,
    contractName: null,
    originalFilename: 'invoice.pdf',
    fileSize: 2048,
    pdfUrl: 'https://example.com/invoice.pdf',
    extractionStatus: 'extracted',
    extractionError: '',
    isPaid: false,
    paymentMatches: [],
    createdAt: '2026-02-01T12:00:00Z',
    createdByName: 'admin@test.local',
    receiverEmails: [],
    uploadStatus: 'uploaded',
    ...overrides,
  }
}

// --- Query result routing ---

type QueryResult = {
  data: unknown
  loading: boolean
  error?: unknown
  refetch: ReturnType<typeof vi.fn>
}

let queryResults: Map<string, QueryResult>

function setQueryData(querySubstring: string, data: unknown) {
  queryResults.set(querySubstring, {
    data,
    loading: false,
    refetch: vi.fn(),
  })
}

function findQueryResult(queryStr: string): QueryResult {
  for (const [substring, result] of queryResults) {
    if (queryStr.includes(substring)) return result
  }
  return { data: null, loading: false, refetch: vi.fn() }
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
  getToken: vi.fn(() => 'mock-token'),
}))

import { useAuth } from '@/lib/auth'

function mockAuth(permissions: string[] = ['invoices.read', 'invoices.generate']) {
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

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/invoices/:id" element={<InvoiceDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  queryResults = new Map()
  mockAuth()
})

describe('InvoiceDetail Router', () => {
  it('routes to generated view by default', () => {
    setQueryData('InvoiceRecord', { invoiceRecord: makeInvoiceRecord() })
    setQueryData('InvoiceAuditLogs', { auditLogs: { edges: [] } })
    renderWithRoute('/invoices/1')
    // Generated view shows billing date label
    expect(screen.getByText('invoiceDetail.billingDate')).toBeInTheDocument()
    expect(screen.getByText('INV-2026-0001')).toBeInTheDocument()
  })

  it('routes to imported view when ?type=imported', () => {
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice() })
    renderWithRoute('/invoices/42?type=imported')
    // Imported view shows the invoice number in the heading
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toHaveTextContent('IMP-2026-0001')
    // Should show metadata section (imported detail specific)
    expect(screen.getByText('importedInvoiceDetail.metadata')).toBeInTheDocument()
  })

  it('falls back to imported view when generated not found', () => {
    setQueryData('InvoiceRecord', { invoiceRecord: null })
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice() })
    setQueryData('InvoiceAuditLogs', { auditLogs: { edges: [] } })
    renderWithRoute('/invoices/42')
    // Should fall back to imported view
    expect(screen.getByText('importedInvoiceDetail.metadata')).toBeInTheDocument()
  })

  it('shows not found when neither type exists', () => {
    setQueryData('InvoiceRecord', { invoiceRecord: null })
    setQueryData('ImportedInvoice', { invoice: null })
    renderWithRoute('/invoices/999?type=imported')
    expect(screen.getByText('invoiceDetail.notFound')).toBeInTheDocument()
  })
})

describe('ImportedInvoiceDetail', () => {
  it('shows Extract button when status is pending', () => {
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice({ extractionStatus: 'pending' }) })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('invoices.import.extract')).toBeInTheDocument()
  })

  it('shows Re-extract button and error when extraction failed', () => {
    setQueryData('ImportedInvoice', {
      invoice: makeImportedInvoice({ extractionStatus: 'extraction_failed', extractionError: 'OCR failed' }),
    })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('invoices.import.reExtract')).toBeInTheDocument()
    expect(screen.getByText('OCR failed')).toBeInTheDocument()
  })

  it('shows Confirm button when status is extracted', () => {
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice({ extractionStatus: 'extracted' }) })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('importedInvoiceDetail.confirm')).toBeInTheDocument()
  })

  it('shows customer link when customer is linked', () => {
    setQueryData('ImportedInvoice', {
      invoice: makeImportedInvoice({ customerId: 5, customerDisplayName: 'Acme Corp' }),
    })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })

  it('shows link customer button when no customer linked', () => {
    setQueryData('ImportedInvoice', {
      invoice: makeImportedInvoice({ customerId: null, customerName: 'Extracted Name' }),
    })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('Extracted Name')).toBeInTheDocument()
    expect(screen.getByText('invoices.import.linkCustomer')).toBeInTheDocument()
  })

  it('shows PDF iframe when uploaded', () => {
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice() })
    renderWithRoute('/invoices/42?type=imported')
    const iframe = document.querySelector('iframe[title="Invoice PDF"]')
    expect(iframe).toBeInTheDocument()
  })

  it('shows PDF pending message when not uploaded', () => {
    setQueryData('ImportedInvoice', {
      invoice: makeImportedInvoice({ uploadStatus: 'pending', pdfUrl: null }),
    })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('importedInvoiceDetail.pdfPending')).toBeInTheDocument()
  })

  it('shows delete button when user has permission', () => {
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice() })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.getByText('common.delete')).toBeInTheDocument()
  })

  it('hides delete button when user lacks permission', () => {
    mockAuth(['invoices.read'])
    setQueryData('ImportedInvoice', { invoice: makeImportedInvoice() })
    renderWithRoute('/invoices/42?type=imported')
    expect(screen.queryByText('common.delete')).not.toBeInTheDocument()
  })

  it('disables link contract when no customer linked', () => {
    setQueryData('ImportedInvoice', {
      invoice: makeImportedInvoice({ customerId: null }),
    })
    renderWithRoute('/invoices/42?type=imported')
    const linkBtn = screen.getByText('importedInvoiceDetail.linkContract')
    expect(linkBtn.closest('button')).toBeDisabled()
  })
})
