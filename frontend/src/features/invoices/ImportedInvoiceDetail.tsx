import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useLazyQuery, gql } from '@apollo/client'
import {
  ArrowLeft,
  Loader2,
  Download,
  Trash2,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Link as LinkIcon,
  Unlink,
  CreditCard,
  Mail,
  FileText,
  Pencil,
  X,
  Save,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { CurrencyInput } from '@/components/ui/currency-input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import { useAuth } from '@/lib/auth'
import { CustomerPickerDialog } from '@/components/CustomerPickerDialog'
import { PaymentMatchModal } from './PaymentMatchModal'

// --- GraphQL ---

const IMPORTED_INVOICE_QUERY = gql`
  query ImportedInvoice($id: ID!) {
    invoice(id: $id) {
      id
      invoiceNumber
      invoiceDate
      totalAmount
      currency
      customerName
      customerId
      customerDisplayName
      contractId
      contractName
      originalFilename
      fileSize
      pdfUrl
      extractionStatus
      extractionError
      isPaid
      paymentMatches {
        id
        transactionId
        transactionDate
        transactionAmount
        counterpartyName
        matchType
        confidence
        matchedAt
        matchedByName
      }
      createdAt
      createdByName
      receiverEmails
      uploadStatus
    }
  }
`

const UPDATE_INVOICE = gql`
  mutation UpdateImportedInvoice($id: ID!, $input: UpdateInvoiceInput!) {
    updateInvoice(id: $id, input: $input) {
      success
      error
      invoice {
        id
        invoiceNumber
        invoiceDate
        totalAmount
        currency
        customerName
      }
    }
  }
`

const EXTRACT_INVOICE = gql`
  mutation ExtractInvoiceDetail($id: ID!) {
    extractInvoice(id: $id) {
      success
      error
      invoice {
        id
        invoiceNumber
        invoiceDate
        totalAmount
        currency
        customerName
        extractionStatus
        extractionError
      }
    }
  }
`

const RE_EXTRACT_INVOICE = gql`
  mutation ReExtractInvoiceDetail($id: ID!) {
    reExtractInvoice(id: $id) {
      success
      error
      invoice {
        id
        invoiceNumber
        invoiceDate
        totalAmount
        currency
        customerName
        extractionStatus
        extractionError
      }
    }
  }
`

const CONFIRM_INVOICE = gql`
  mutation ConfirmInvoiceDetail($id: ID!) {
    confirmInvoice(id: $id) {
      success
      error
      invoice {
        id
        extractionStatus
      }
    }
  }
`

const DELETE_INVOICE = gql`
  mutation DeleteImportedInvoiceDetail($id: ID!) {
    deleteInvoice(id: $id) {
      success
      error
    }
  }
`

const CONFIRM_CUSTOMER_MATCH = gql`
  mutation ConfirmCustomerMatchDetail($invoiceId: ID!, $customerId: Int!) {
    confirmCustomerMatch(invoiceId: $invoiceId, customerId: $customerId) {
      success
      error
      invoice {
        id
        customerId
        customerDisplayName
      }
    }
  }
`

const UNLINK_CUSTOMER = gql`
  mutation UnlinkCustomerDetail($invoiceId: ID!) {
    unlinkCustomerFromInvoice(invoiceId: $invoiceId) {
      success
      error
      invoice {
        id
        customerId
        customerDisplayName
        contractId
      }
    }
  }
`

const ASSIGN_INVOICE_CONTRACT = gql`
  mutation AssignInvoiceContractDetail($invoiceId: ID!, $contractId: Int) {
    assignInvoiceContract(invoiceId: $invoiceId, contractId: $contractId) {
      success
      error
      invoice {
        id
        contractId
        contractName
      }
    }
  }
`

const CUSTOMER_MATCH_SUGGESTIONS = gql`
  query CustomerMatchSuggestionsDetail($invoiceId: ID!) {
    customerMatchSuggestions(invoiceId: $invoiceId) {
      customerId
      customerName
      city
      similarity
      hubspotId
    }
  }
`

const CUSTOMER_CONTRACTS = gql`
  query CustomerContractsForInvoice($id: ID!) {
    customer(id: $id) {
      id
      contracts {
        id
        name
        status
      }
    }
  }
`

// --- Types ---

interface PaymentMatch {
  id: number
  transactionId: number
  transactionDate: string
  transactionAmount: string
  counterpartyName: string
  matchType: string
  confidence: string
  matchedAt: string
  matchedByName: string | null
}

interface ImportedInvoice {
  id: string
  invoiceNumber: string
  invoiceDate: string | null
  totalAmount: string | null
  currency: string
  customerName: string
  customerId: number | null
  customerDisplayName: string | null
  contractId: number | null
  contractName: string | null
  originalFilename: string
  fileSize: number
  pdfUrl: string | null
  extractionStatus: string
  extractionError: string
  isPaid: boolean
  paymentMatches: PaymentMatch[]
  createdAt: string
  createdByName: string | null
  receiverEmails: string[]
  uploadStatus: string
}

interface CustomerMatch {
  customerId: number
  customerName: string
  city: string | null
  similarity: string
  hubspotId: string | null
}

// --- Helpers ---

function ExtractionStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  switch (status) {
    case 'pending':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-1 text-sm font-medium text-gray-600">
          {t('invoices.import.statusPending')}
        </span>
      )
    case 'extracting':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-sm font-medium text-blue-700">
          <Loader2 className="h-3 w-3 animate-spin" />
          {t('invoices.import.statusExtracting')}
        </span>
      )
    case 'extracted':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-1 text-sm font-medium text-amber-700">
          {t('invoices.import.statusExtracted')}
        </span>
      )
    case 'confirmed':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-sm font-medium text-green-800">
          <CheckCircle className="h-3 w-3" />
          {t('invoices.import.statusConfirmed')}
        </span>
      )
    case 'extraction_failed':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-sm font-medium text-red-700">
          <AlertCircle className="h-3 w-3" />
          {t('invoices.import.statusFailed')}
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-1 text-sm font-medium text-gray-600">
          {status}
        </span>
      )
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDateTime(dateStr: string, locale: string) {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return d.toLocaleString(locale === 'de' ? 'de-DE' : 'en-GB', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// --- Main Component ---

export function ImportedInvoiceDetail({ id }: { id: number }) {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { hasPermission } = useAuth()
  const canWrite = hasPermission('invoices', 'generate')

  // State
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showCustomerPicker, setShowCustomerPicker] = useState(false)
  const [showContractPicker, setShowContractPicker] = useState(false)
  const [showPaymentModal, setShowPaymentModal] = useState(false)

  // Inline editing state
  const [editing, setEditing] = useState<'invoiceNumber' | 'invoiceDate' | 'totalAmount' | null>(null)
  const [editValue, setEditValue] = useState('')

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000)
      return () => clearTimeout(timer)
    }
  }, [toast])

  // Queries
  const { data, loading, error, refetch } = useQuery<{ invoice: ImportedInvoice | null }>(
    IMPORTED_INVOICE_QUERY,
    { variables: { id } }
  )

  const [fetchSuggestions, { data: suggestionsData, loading: loadingSuggestions }] = useLazyQuery(
    CUSTOMER_MATCH_SUGGESTIONS
  )

  const [fetchContracts, { data: contractsData, loading: loadingContracts }] = useLazyQuery(
    CUSTOMER_CONTRACTS
  )

  // Mutations
  const [updateInvoice] = useMutation(UPDATE_INVOICE)
  const [extractInvoice, { loading: extracting }] = useMutation(EXTRACT_INVOICE)
  const [reExtractInvoice, { loading: reExtracting }] = useMutation(RE_EXTRACT_INVOICE)
  const [confirmInvoice, { loading: confirming }] = useMutation(CONFIRM_INVOICE)
  const [deleteInvoice, { loading: deleting }] = useMutation(DELETE_INVOICE)
  const [confirmCustomerMatch] = useMutation(CONFIRM_CUSTOMER_MATCH)
  const [unlinkCustomer] = useMutation(UNLINK_CUSTOMER)
  const [assignContract] = useMutation(ASSIGN_INVOICE_CONTRACT)

  const invoice = data?.invoice
  const suggestions: CustomerMatch[] = suggestionsData?.customerMatchSuggestions || []

  // Handlers
  const handleExtract = async () => {
    if (!invoice) return
    try {
      const result = await extractInvoice({ variables: { id: invoice.id } })
      if (result.data?.extractInvoice?.success) {
        setToast({ type: 'success', message: t('importedInvoiceDetail.extractStarted') })
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.extractInvoice?.error || t('importedInvoiceDetail.extractFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.extractFailed') })
    }
  }

  const handleReExtract = async () => {
    if (!invoice) return
    try {
      const result = await reExtractInvoice({ variables: { id: invoice.id } })
      if (result.data?.reExtractInvoice?.success) {
        setToast({ type: 'success', message: t('importedInvoiceDetail.extractStarted') })
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.reExtractInvoice?.error || t('importedInvoiceDetail.extractFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.extractFailed') })
    }
  }

  const handleConfirm = async () => {
    if (!invoice) return
    try {
      const result = await confirmInvoice({ variables: { id: invoice.id } })
      if (result.data?.confirmInvoice?.success) {
        setToast({ type: 'success', message: t('importedInvoiceDetail.confirmed') })
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.confirmInvoice?.error || t('importedInvoiceDetail.confirmFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.confirmFailed') })
    }
  }

  const handleDelete = async () => {
    if (!invoice) return
    setShowDeleteDialog(false)
    try {
      const result = await deleteInvoice({ variables: { id: invoice.id } })
      if (result.data?.deleteInvoice?.success) {
        navigate('/invoices')
      } else {
        setToast({ type: 'error', message: result.data?.deleteInvoice?.error || t('importedInvoiceDetail.deleteFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.deleteFailed') })
    }
  }

  const handleSaveField = async () => {
    if (!invoice || !editing) return
    const input: Record<string, string | null> = {}
    if (editing === 'invoiceNumber') input.invoiceNumber = editValue
    if (editing === 'invoiceDate') input.invoiceDate = editValue || null
    if (editing === 'totalAmount') input.totalAmount = editValue || null

    try {
      const result = await updateInvoice({ variables: { id: invoice.id, input } })
      if (result.data?.updateInvoice?.success) {
        setEditing(null)
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.updateInvoice?.error || t('importedInvoiceDetail.saveFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.saveFailed') })
    }
  }

  const handleLinkCustomer = async (customerId: number) => {
    if (!invoice) return
    try {
      const result = await confirmCustomerMatch({
        variables: { invoiceId: invoice.id, customerId },
      })
      if (result.data?.confirmCustomerMatch?.success) {
        setShowCustomerPicker(false)
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.confirmCustomerMatch?.error || t('importedInvoiceDetail.linkFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.linkFailed') })
    }
  }

  const handleUnlinkCustomer = async () => {
    if (!invoice) return
    try {
      const result = await unlinkCustomer({ variables: { invoiceId: invoice.id } })
      if (result.data?.unlinkCustomerFromInvoice?.success) {
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.unlinkCustomerFromInvoice?.error || t('importedInvoiceDetail.unlinkFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.unlinkFailed') })
    }
  }

  const handleLinkContract = async (contractId: number) => {
    if (!invoice) return
    try {
      const result = await assignContract({
        variables: { invoiceId: invoice.id, contractId },
      })
      if (result.data?.assignInvoiceContract?.success) {
        setShowContractPicker(false)
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.assignInvoiceContract?.error || t('importedInvoiceDetail.linkFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.linkFailed') })
    }
  }

  const handleUnlinkContract = async () => {
    if (!invoice) return
    try {
      const result = await assignContract({
        variables: { invoiceId: invoice.id, contractId: null },
      })
      if (result.data?.assignInvoiceContract?.success) {
        refetch()
      } else {
        setToast({ type: 'error', message: result.data?.assignInvoiceContract?.error || t('importedInvoiceDetail.unlinkFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('importedInvoiceDetail.unlinkFailed') })
    }
  }

  const openCustomerPicker = () => {
    if (invoice) {
      fetchSuggestions({ variables: { invoiceId: invoice.id } })
    }
    setShowCustomerPicker(true)
  }

  const openContractPicker = () => {
    if (invoice?.customerId) {
      fetchContracts({ variables: { id: invoice.customerId } })
    }
    setShowContractPicker(true)
  }

  const openPaymentModal = () => {
    setShowPaymentModal(true)
  }

  // Loading
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Not found
  if (error || !invoice) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <button onClick={() => navigate(-1)} className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </button>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t('invoiceDetail.notFound')}
          </CardContent>
        </Card>
      </div>
    )
  }

  const isEditable = invoice.extractionStatus === 'extracted' || invoice.extractionStatus === 'confirmed'

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed right-4 top-4 z-50 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
            toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {invoice.invoiceNumber || invoice.originalFilename}
            </h1>
            <div className="mt-1 flex items-center gap-3">
              <ExtractionStatusBadge status={invoice.extractionStatus} />
              {invoice.isPaid && (
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-sm font-medium text-green-800">
                  <CheckCircle className="h-4 w-4" />
                  {t('invoices.import.paid')}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* Extraction actions */}
            {invoice.extractionStatus === 'pending' && (
              <Button variant="outline" size="sm" onClick={handleExtract} disabled={extracting}>
                {extracting ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1 h-4 w-4" />}
                {t('invoices.import.extract')}
              </Button>
            )}
            {invoice.extractionStatus === 'extraction_failed' && (
              <Button variant="outline" size="sm" onClick={handleReExtract} disabled={reExtracting}>
                {reExtracting ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-1 h-4 w-4" />}
                {t('invoices.import.reExtract')}
              </Button>
            )}
            {invoice.extractionStatus === 'extracted' && (
              <Button variant="outline" size="sm" onClick={handleConfirm} disabled={confirming}>
                {confirming ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-1 h-4 w-4" />}
                {t('importedInvoiceDetail.confirm')}
              </Button>
            )}
            {/* Download PDF */}
            {invoice.pdfUrl && (
              <Button variant="outline" size="sm" asChild>
                <a href={invoice.pdfUrl} target="_blank" rel="noopener noreferrer">
                  <Download className="mr-1 h-4 w-4" />
                  {t('invoiceDetail.downloadPdf')}
                </a>
              </Button>
            )}
            {/* Delete */}
            {canWrite && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
                disabled={deleting}
              >
                <Trash2 className="mr-1 h-4 w-4" />
                {t('common.delete')}
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-6 lg:col-span-2">
          {/* Metadata card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                {t('importedInvoiceDetail.metadata')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                {/* Invoice Number */}
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoices.invoiceNo')}
                  </div>
                  {editing === 'invoiceNumber' ? (
                    <div className="mt-1 flex items-center gap-1">
                      <Input
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="h-8 text-sm"
                        autoFocus
                      />
                      <Button variant="ghost" size="sm" onClick={handleSaveField} className="h-8 w-8 p-0">
                        <Save className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(null)} className="h-8 w-8 p-0">
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <div className="mt-1 flex items-center gap-1">
                      <span className="font-medium">{invoice.invoiceNumber || '-'}</span>
                      {isEditable && (
                        <button
                          onClick={() => { setEditing('invoiceNumber'); setEditValue(invoice.invoiceNumber || '') }}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Invoice Date */}
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('importedInvoiceDetail.invoiceDate')}
                  </div>
                  {editing === 'invoiceDate' ? (
                    <div className="mt-1 flex items-center gap-1">
                      <Input
                        type="date"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="h-8 text-sm"
                        autoFocus
                      />
                      <Button variant="ghost" size="sm" onClick={handleSaveField} className="h-8 w-8 p-0">
                        <Save className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(null)} className="h-8 w-8 p-0">
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <div className="mt-1 flex items-center gap-1">
                      <span className="font-medium">
                        {invoice.invoiceDate ? formatDate(invoice.invoiceDate) : '-'}
                      </span>
                      {isEditable && (
                        <button
                          onClick={() => { setEditing('invoiceDate'); setEditValue(invoice.invoiceDate || '') }}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Amount */}
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoices.amount')}
                  </div>
                  {editing === 'totalAmount' ? (
                    <div className="mt-1 flex items-center gap-1">
                      <CurrencyInput
                        value={editValue}
                        onChange={setEditValue}
                        className="h-8 text-sm"
                        autoFocus
                      />
                      <Button variant="ghost" size="sm" onClick={handleSaveField} className="h-8 w-8 p-0">
                        <Save className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setEditing(null)} className="h-8 w-8 p-0">
                        <X className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <div className="mt-1 flex items-center gap-1">
                      <span className="font-medium">
                        {invoice.totalAmount
                          ? `${formatCurrency(invoice.totalAmount)} ${invoice.currency !== 'EUR' ? invoice.currency : ''}`
                          : '-'}
                      </span>
                      {isEditable && (
                        <button
                          onClick={() => { setEditing('totalAmount'); setEditValue(invoice.totalAmount || '') }}
                          className="text-muted-foreground hover:text-foreground"
                        >
                          <Pencil className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('importedInvoiceDetail.originalFile')}
                  </div>
                  <div className="mt-1 font-medium">{invoice.originalFilename}</div>
                  <div className="text-xs text-muted-foreground">{formatFileSize(invoice.fileSize)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('importedInvoiceDetail.createdBy')}
                  </div>
                  <div className="mt-1 font-medium">{invoice.createdByName || '-'}</div>
                  <div className="text-xs text-muted-foreground">{formatDateTime(invoice.createdAt, i18n.language)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('importedInvoiceDetail.extractionStatus')}
                  </div>
                  <div className="mt-1">
                    <ExtractionStatusBadge status={invoice.extractionStatus} />
                  </div>
                </div>
              </div>

              {/* Extraction error */}
              {invoice.extractionStatus === 'extraction_failed' && invoice.extractionError && (
                <div className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  <div className="flex items-center gap-2 font-medium">
                    <AlertCircle className="h-4 w-4" />
                    {t('importedInvoiceDetail.extractionError')}
                  </div>
                  <p className="mt-1">{invoice.extractionError}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* PDF Preview */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {t('importedInvoiceDetail.pdfPreview')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.uploadStatus === 'pending' ? (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  <FileText className="mx-auto mb-2 h-8 w-8" />
                  {t('importedInvoiceDetail.pdfPending')}
                </div>
              ) : invoice.pdfUrl ? (
                <iframe
                  src={invoice.pdfUrl}
                  className="h-[600px] w-full rounded border"
                  title="Invoice PDF"
                />
              ) : (
                <div className="py-12 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.noPreview')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Customer card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('invoiceDetail.customer')}</CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.customerId ? (
                <div className="flex items-center justify-between">
                  <Link
                    to={`/customers/${invoice.customerId}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {invoice.customerDisplayName || invoice.customerName}
                  </Link>
                  <button
                    onClick={handleUnlinkCustomer}
                    disabled={!!invoice.contractId}
                    className={cn(
                      'text-sm',
                      invoice.contractId
                        ? 'cursor-not-allowed text-gray-300'
                        : 'text-muted-foreground hover:text-red-600'
                    )}
                    title={invoice.contractId ? t('invoices.import.unlinkCustomerDisabled') : t('invoices.import.unlinkCustomer')}
                  >
                    <Unlink className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div>
                  {invoice.customerName && (
                    <p className="mb-2 text-sm text-muted-foreground">{invoice.customerName}</p>
                  )}
                  <Button variant="outline" size="sm" onClick={openCustomerPicker}>
                    <LinkIcon className="mr-1 h-4 w-4" />
                    {t('invoices.import.linkCustomer')}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Contract card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('invoiceDetail.contract')}</CardTitle>
            </CardHeader>
            <CardContent>
              {invoice.contractId ? (
                <div className="flex items-center justify-between">
                  <Link
                    to={`/contracts/${invoice.contractId}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {invoice.contractName}
                  </Link>
                  <button
                    onClick={handleUnlinkContract}
                    className="text-sm text-muted-foreground hover:text-red-600"
                  >
                    <Unlink className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={openContractPicker}
                    disabled={!invoice.customerId}
                  >
                    <LinkIcon className="mr-1 h-4 w-4" />
                    {t('importedInvoiceDetail.linkContract')}
                  </Button>
                  {!invoice.customerId && (
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t('importedInvoiceDetail.linkContractRequiresCustomer')}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Payment Matches */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2 text-base">
                  <CreditCard className="h-4 w-4" />
                  {t('invoiceDetail.payments')}
                </CardTitle>
                {!invoice.isPaid && invoice.extractionStatus !== 'pending' && (
                  <Button variant="ghost" size="sm" onClick={openPaymentModal}>
                    <CreditCard className="mr-1 h-4 w-4" />
                    {t('invoices.import.matchPayment')}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {invoice.paymentMatches.length > 0 ? (
                <div className="space-y-3">
                  {invoice.paymentMatches.map((match) => (
                    <div key={match.id} className="rounded border p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {formatCurrency(match.transactionAmount)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(match.transactionDate)}
                        </span>
                      </div>
                      <div className="mt-1 text-muted-foreground">{match.counterpartyName}</div>
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="rounded bg-muted px-1.5 py-0.5">{match.matchType}</span>
                        <span>{Math.round(Number(match.confidence) * 100)}%</span>
                        {match.matchedByName && <span>by {match.matchedByName}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.noPayments')}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Receiver Emails */}
          {invoice.receiverEmails && invoice.receiverEmails.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Mail className="h-4 w-4" />
                  {t('importedInvoiceDetail.receiverEmails')}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {invoice.receiverEmails.map((email, i) => (
                    <div key={i} className="text-sm">{email}</div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('invoices.import.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('invoices.import.deleteConfirmation')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Customer Picker Dialog */}
      <CustomerPickerDialog
        open={showCustomerPicker}
        onOpenChange={setShowCustomerPicker}
        title={t('invoices.import.matchCustomerTitle')}
        description={invoice.customerName ? t('invoices.import.matchCustomerDescription', { name: invoice.customerName }) : undefined}
        onSelect={handleLinkCustomer}
        loading={loadingSuggestions}
      >
        {suggestions.length > 0 ? (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-muted-foreground">{t('invoices.import.suggestedCustomers')}</h4>
            {suggestions.map((match) => (
              <button
                key={match.customerId}
                onClick={() => handleLinkCustomer(match.customerId)}
                className="w-full rounded-lg border p-3 text-left hover:bg-muted/50"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">{match.customerName}</div>
                    {match.city && <div className="text-sm text-muted-foreground">{match.city}</div>}
                  </div>
                  <Badge variant="secondary">
                    {Math.round(parseFloat(match.similarity) * 100)}%
                  </Badge>
                </div>
              </button>
            ))}
          </div>
        ) : !loadingSuggestions ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            <AlertCircle className="mx-auto mb-2 h-8 w-8" />
            <p>{t('invoices.import.noCustomerMatches')}</p>
          </div>
        ) : null}
      </CustomerPickerDialog>

      {/* Contract Picker Dialog */}
      <Dialog open={showContractPicker} onOpenChange={setShowContractPicker}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('importedInvoiceDetail.selectContract')}</DialogTitle>
            <DialogDescription>{t('importedInvoiceDetail.selectContractDescription')}</DialogDescription>
          </DialogHeader>
          <div className="max-h-80 space-y-2 overflow-y-auto py-2">
            {loadingContracts ? (
              <div className="py-4 text-center">
                <Loader2 className="mx-auto h-6 w-6 animate-spin" />
              </div>
            ) : contractsData?.customer?.contracts?.length ? (
              contractsData.customer.contracts.map((c: { id: string; name: string; status: string }) => (
                <button
                  key={c.id}
                  onClick={() => handleLinkContract(Number(c.id))}
                  className="w-full rounded-lg border p-3 text-left hover:bg-muted/50"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{c.name}</span>
                    <Badge variant="outline" className="text-xs">{c.status}</Badge>
                  </div>
                </button>
              ))
            ) : (
              <p className="py-4 text-center text-sm text-muted-foreground">
                {t('importedInvoiceDetail.noContracts')}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowContractPicker(false)}>
              {t('common.cancel')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment Match Modal */}
      <PaymentMatchModal
        open={showPaymentModal}
        onOpenChange={setShowPaymentModal}
        invoiceId={invoice.id}
        invoiceNumber={invoice.invoiceNumber || invoice.originalFilename}
        amount={invoice.totalAmount}
        customerName={invoice.customerDisplayName || invoice.customerName || ''}
        isPaid={invoice.isPaid}
        existingMatches={invoice.paymentMatches}
        onMatchChanged={() => {
          setShowPaymentModal(false)
          refetch()
        }}
      />
    </div>
  )
}
