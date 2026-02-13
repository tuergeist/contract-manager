import { useState, useRef, useCallback, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useLazyQuery, gql } from '@apollo/client'
import {
  Upload,
  Loader2,
  Trash2,
  Search,
  Check,
  FileText,
  RefreshCw,
  Link as LinkIcon,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Unlink,
  FileSpreadsheet,
  Mail,
  X,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import { useAuth } from '@/lib/auth'

// --- GraphQL ---

const IMPORTED_INVOICES = gql`
  query ImportedInvoices(
    $search: String
    $paymentStatus: PaymentStatusFilter
    $uploadStatus: UploadStatusFilter
    $sortBy: String
    $sortOrder: String
    $offset: Int
    $limit: Int
  ) {
    importedInvoices(
      search: $search
      paymentStatus: $paymentStatus
      uploadStatus: $uploadStatus
      sortBy: $sortBy
      sortOrder: $sortOrder
      offset: $offset
      limit: $limit
    ) {
      items {
        id
        invoiceNumber
        invoiceDate
        totalAmount
        currency
        customerName
        customerId
        customerDisplayName
        contractId
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
        }
        createdAt
        createdByName
        expectedFilename
        receiverEmails
        uploadStatus
        importBatchId
      }
      totalCount
      hasNextPage
    }
  }
`

const DELETE_INVOICE = gql`
  mutation DeleteImportedInvoice($id: ID!) {
    deleteImportedInvoice(id: $id) {
      success
      error
    }
  }
`

const EXTRACT_INVOICE = gql`
  mutation ExtractInvoice($id: ID!) {
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
  mutation ReExtractInvoice($id: ID!) {
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

const CUSTOMER_MATCH_SUGGESTIONS = gql`
  query CustomerMatchSuggestions($invoiceId: ID!) {
    customerMatchSuggestions(invoiceId: $invoiceId) {
      customerId
      customerName
      city
      similarity
      hubspotId
    }
  }
`

const CONFIRM_CUSTOMER_MATCH = gql`
  mutation ConfirmCustomerMatch($invoiceId: ID!, $customerId: Int!) {
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
  mutation UnlinkCustomerFromInvoice($invoiceId: ID!) {
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

const FIND_PAYMENT_MATCHES = gql`
  query FindPaymentMatches($invoiceId: ID!, $daysAfter: Int) {
    findPaymentMatches(invoiceId: $invoiceId, daysAfter: $daysAfter) {
      transactionId
      transactionDate
      amount
      counterpartyName
      bookingText
      matchType
      confidence
    }
  }
`

const SEARCH_TRANSACTIONS = gql`
  query SearchTransactions($search: String, $direction: String, $page: Int, $pageSize: Int) {
    bankTransactions(search: $search, direction: $direction, page: $page, pageSize: $pageSize) {
      items {
        id
        entryDate
        amount
        currency
        counterparty {
          name
        }
        bookingText
      }
      totalCount
    }
  }
`

const CREATE_PAYMENT_MATCH = gql`
  mutation CreatePaymentMatch($invoiceId: ID!, $transactionId: Int!, $matchType: String) {
    createPaymentMatch(invoiceId: $invoiceId, transactionId: $transactionId, matchType: $matchType) {
      success
      error
      match {
        id
        transactionId
        transactionDate
        transactionAmount
        counterpartyName
        matchType
        confidence
      }
    }
  }
`

const DELETE_PAYMENT_MATCH = gql`
  mutation DeletePaymentMatch($matchId: Int!) {
    deletePaymentMatch(matchId: $matchId) {
      success
      error
    }
  }
`

const IMPORT_BATCHES = gql`
  query ImportBatches($offset: Int, $limit: Int) {
    importBatches(offset: $offset, limit: $limit) {
      items {
        id
        name
        totalExpected
        totalUploaded
        pendingCount
        createdAt
        createdByName
      }
      totalCount
      hasNextPage
    }
  }
`

const UPLOAD_INVOICE_CSV = gql`
  mutation UploadInvoiceCsv($input: UploadInvoiceCsvInput!) {
    uploadInvoiceCsv(input: $input) {
      success
      error
      batch {
        id
        name
        totalExpected
        totalUploaded
        pendingCount
      }
      rowsProcessed
    }
  }
`

const UPLOAD_INVOICES = gql`
  mutation UploadInvoices($inputs: [BulkUploadInvoiceInput!]!) {
    uploadInvoices(inputs: $inputs) {
      success
      error
      results {
        filename
        success
        error
        invoice {
          id
          invoiceNumber
        }
        matchedExpected
      }
      totalUploaded
      totalFailed
    }
  }
`

const DELETE_IMPORT_BATCH = gql`
  mutation DeleteImportBatch($id: ID!) {
    deleteImportBatch(id: $id) {
      success
      error
    }
  }
`

const SEARCH_CUSTOMERS = gql`
  query SearchCustomers($search: String!) {
    customers(search: $search) {
      items {
        id
        name
        address
        hubspotId
      }
    }
  }
`

interface ImportBatch {
  id: string
  name: string
  totalExpected: number
  totalUploaded: number
  pendingCount: number
  createdAt: string
  createdByName: string | null
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
  originalFilename: string
  fileSize: number
  pdfUrl: string | null
  extractionStatus: string
  extractionError: string
  isPaid: boolean
  paymentMatches: {
    id: number
    transactionId: number
    transactionDate: string
    transactionAmount: string
    counterpartyName: string
    matchType: string
    confidence: string
  }[]
  createdAt: string
  createdByName: string | null
  // New fields for receiver mapping
  expectedFilename: string
  receiverEmails: string[]
  uploadStatus: string
  importBatchId: number | null
}

interface CustomerMatch {
  customerId: number
  customerName: string
  city: string | null
  similarity: string
  hubspotId: string | null
}

interface PaymentMatchCandidate {
  transactionId: number
  transactionDate: string
  amount: string
  counterpartyName: string
  bookingText: string
  matchType: string
  confidence: string
}

interface SearchTransaction {
  id: number
  entryDate: string
  amount: string
  currency: string
  counterparty: { name: string } | null
  bookingText: string
}

export function ImportedInvoiceList() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  // State
  const [search, setSearch] = useState('')
  const [paymentStatus, setPaymentStatus] = useState<string>('ALL')
  const [uploadStatus, setUploadStatus] = useState<string>('ALL')
  const [page, setPage] = useState(1)
  const [sortField, setSortField] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const pageSize = 20

  // Modals
  const [uploadOpen, setUploadOpen] = useState(false)
  const [csvUploadOpen, setCsvUploadOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteBatchId, setDeleteBatchId] = useState<string | null>(null)
  const [customerMatchInvoice, setCustomerMatchInvoice] = useState<ImportedInvoice | null>(null)
  const [paymentMatchInvoice, setPaymentMatchInvoice] = useState<ImportedInvoice | null>(null)
  const [transactionSearch, setTransactionSearch] = useState('')
  const [debouncedTxSearch, setDebouncedTxSearch] = useState('')
  const [customerSearch, setCustomerSearch] = useState('')
  const [debouncedCustomerSearch, setDebouncedCustomerSearch] = useState('')

  // File upload
  const fileInputRef = useRef<HTMLInputElement>(null)
  const csvInputRef = useRef<HTMLInputElement>(null)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ filename: string; status: 'pending' | 'success' | 'error'; error?: string }[]>([])

  // Queries & Mutations
  const { data, loading, refetch, startPolling, stopPolling } = useQuery(IMPORTED_INVOICES, {
    variables: {
      search: search || null,
      paymentStatus: paymentStatus === 'ALL' ? null : paymentStatus,
      uploadStatus: uploadStatus === 'ALL' ? null : uploadStatus,
      sortBy: sortField,
      sortOrder: sortField ? sortOrder : null,
      offset: (page - 1) * pageSize,
      limit: pageSize,
    },
    fetchPolicy: 'cache-and-network',
  })

  // Poll for updates when any invoice is being extracted
  useEffect(() => {
    const items = data?.importedInvoices?.items || []
    const hasExtracting = items.some(
      (inv: ImportedInvoice) => inv.extractionStatus === 'extracting'
    )

    if (hasExtracting) {
      startPolling(2000) // Poll every 2 seconds
    } else {
      stopPolling()
    }

    return () => stopPolling()
  }, [data?.importedInvoices?.items, startPolling, stopPolling])

  const { data: batchData, refetch: refetchBatches } = useQuery(IMPORT_BATCHES, {
    variables: { offset: 0, limit: 10 },
    fetchPolicy: 'cache-and-network',
  })

  const [uploadInvoicesMutation] = useMutation(UPLOAD_INVOICES)
  const [uploadInvoiceCsvMutation] = useMutation(UPLOAD_INVOICE_CSV)
  const [deleteInvoiceMutation] = useMutation(DELETE_INVOICE)
  const [deleteImportBatchMutation] = useMutation(DELETE_IMPORT_BATCH)
  const [extractInvoiceMutation] = useMutation(EXTRACT_INVOICE)
  const [reExtractInvoiceMutation] = useMutation(RE_EXTRACT_INVOICE)
  const [confirmCustomerMatchMutation] = useMutation(CONFIRM_CUSTOMER_MATCH)
  const [unlinkCustomerMutation] = useMutation(UNLINK_CUSTOMER)
  const [createPaymentMatchMutation] = useMutation(CREATE_PAYMENT_MATCH)
  const [deletePaymentMatchMutation] = useMutation(DELETE_PAYMENT_MATCH)

  const [findPaymentMatches, { data: paymentMatchData, loading: loadingPaymentMatches }] = useLazyQuery(
    FIND_PAYMENT_MATCHES,
    { fetchPolicy: 'network-only' }
  )

  const { data: searchTxData, loading: loadingTxSearch } = useQuery(
    SEARCH_TRANSACTIONS,
    {
      variables: { search: debouncedTxSearch, direction: 'credit', page: 1, pageSize: 20 },
      skip: !paymentMatchInvoice || !debouncedTxSearch,
    }
  )

  // Debounce transaction search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTxSearch(transactionSearch), 300)
    return () => clearTimeout(timer)
  }, [transactionSearch])

  // Debounce customer search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedCustomerSearch(customerSearch), 300)
    return () => clearTimeout(timer)
  }, [customerSearch])

  // Fetch payment matches when invoice selected
  useEffect(() => {
    if (paymentMatchInvoice) {
      findPaymentMatches({ variables: { invoiceId: paymentMatchInvoice.id, daysAfter: 90 } })
    }
  }, [paymentMatchInvoice, findPaymentMatches])

  const { data: customerMatchData, loading: loadingCustomerMatches } = useQuery(
    CUSTOMER_MATCH_SUGGESTIONS,
    {
      variables: { invoiceId: customerMatchInvoice?.id },
      skip: !customerMatchInvoice,
    }
  )

  const { data: customerSearchData, loading: loadingCustomerSearch } = useQuery(
    SEARCH_CUSTOMERS,
    {
      variables: { search: debouncedCustomerSearch },
      skip: !customerMatchInvoice || !debouncedCustomerSearch || debouncedCustomerSearch.length < 2,
    }
  )

  const invoices: ImportedInvoice[] = data?.importedInvoices?.items ?? []
  const totalCount = data?.importedInvoices?.totalCount ?? 0
  const hasNextPage = data?.importedInvoices?.hasNextPage ?? false
  const totalPages = Math.ceil(totalCount / pageSize)
  const batches: ImportBatch[] = batchData?.importBatches?.items ?? []

  // Sort handling
  const handleSort = (field: string) => {
    if (sortField === field) {
      if (sortOrder === 'desc') {
        setSortOrder('asc')
      } else {
        setSortField(null)
        setSortOrder('desc')
      }
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const getSortIcon = (field: string) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 inline h-3 w-3 opacity-50" />
    }
    return sortOrder === 'desc' ? (
      <ArrowDown className="ml-1 inline h-3 w-3" />
    ) : (
      <ArrowUp className="ml-1 inline h-3 w-3" />
    )
  }

  // Handlers
  const handleMultiFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []).filter(f => f.type === 'application/pdf')
    setUploadFiles(files)
    setUploadProgress(files.map(f => ({ filename: f.name, status: 'pending' as const })))
  }, [])

  const handleCsvSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && (file.type === 'text/csv' || file.name.endsWith('.csv'))) {
      setCsvFile(file)
    }
  }, [])

  const handleDelete = async () => {
    if (!deleteId) return
    await deleteInvoiceMutation({ variables: { id: deleteId } })
    setDeleteId(null)
    refetch()
  }

  const handleDeleteBatch = async () => {
    if (!deleteBatchId) return
    await deleteImportBatchMutation({ variables: { id: deleteBatchId } })
    setDeleteBatchId(null)
    refetch()
    refetchBatches()
  }

  const handleCsvUpload = async () => {
    if (!csvFile) return

    setUploading(true)
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1]
        const result = await uploadInvoiceCsvMutation({
          variables: {
            input: {
              fileContent: base64,
              filename: csvFile.name,
            },
          },
        })

        if (result.data?.uploadInvoiceCsv?.success) {
          refetch()
          refetchBatches()
          setCsvUploadOpen(false)
          setCsvFile(null)
        }
      }
      reader.readAsDataURL(csvFile)
    } finally {
      setUploading(false)
    }
  }

  const handleBulkUpload = async () => {
    if (uploadFiles.length === 0) return

    setUploading(true)
    try {
      // Read all files as base64
      const fileContents = await Promise.all(
        uploadFiles.map(file => new Promise<{ filename: string; content: string }>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => {
            const base64 = (reader.result as string).split(',')[1]
            resolve({ filename: file.name, content: base64 })
          }
          reader.onerror = reject
          reader.readAsDataURL(file)
        }))
      )

      const result = await uploadInvoicesMutation({
        variables: {
          inputs: fileContents.map(f => ({
            fileContent: f.content,
            filename: f.filename,
          })),
        },
      })

      if (result.data?.uploadInvoices?.success) {
        // Update progress with results
        const results = result.data.uploadInvoices.results || []
        setUploadProgress(
          results.map((r: { filename: string; success: boolean; error?: string; matchedExpected?: boolean }) => ({
            filename: r.filename,
            status: r.success ? 'success' as const : 'error' as const,
            error: r.error,
            matchedExpected: r.matchedExpected,
          }))
        )

        // Trigger extraction for successful uploads
        for (const r of results) {
          if (r.success && r.invoice?.id) {
            extractInvoiceMutation({ variables: { id: r.invoice.id } })
          }
        }

        refetch()
        refetchBatches()
      }
    } finally {
      setUploading(false)
    }
  }

  const closeBulkUploadModal = () => {
    setUploadOpen(false)
    setUploadFiles([])
    setUploadProgress([])
  }

  const handleExtract = async (id: string) => {
    await extractInvoiceMutation({ variables: { id } })
    refetch()
  }

  const handleReExtract = async (id: string) => {
    await reExtractInvoiceMutation({ variables: { id } })
    refetch()
  }

  const handleConfirmCustomer = async (customerId: number | string) => {
    if (!customerMatchInvoice) return
    await confirmCustomerMatchMutation({
      variables: {
        invoiceId: customerMatchInvoice.id,
        customerId: typeof customerId === 'string' ? parseInt(customerId, 10) : customerId,
      },
    })
    setCustomerMatchInvoice(null)
    refetch()
  }

  const handleUnlinkCustomer = async (invoiceId: string) => {
    await unlinkCustomerMutation({ variables: { invoiceId } })
    refetch()
  }

  const handleCreatePaymentMatch = async (transactionId: number, matchType: string = 'manual') => {
    if (!paymentMatchInvoice) return
    const result = await createPaymentMatchMutation({
      variables: {
        invoiceId: paymentMatchInvoice.id,
        transactionId,
        matchType,
      },
    })
    if (result.data?.createPaymentMatch?.success) {
      setPaymentMatchInvoice(null)
      setTransactionSearch('')
      refetch()
    }
  }

  const handleDeletePaymentMatch = async (matchId: number) => {
    const result = await deletePaymentMatchMutation({
      variables: { matchId },
    })
    if (result.data?.deletePaymentMatch?.success) {
      refetch()
    }
  }

  const openPaymentMatchModal = (invoice: ImportedInvoice) => {
    setPaymentMatchInvoice(invoice)
    setTransactionSearch('')
  }

  const getStatusBadge = (invoice: ImportedInvoice) => {
    const status = invoice.extractionStatus
    switch (status) {
      case 'pending':
        return <Badge variant="secondary">{t('invoices.import.statusPending')}</Badge>
      case 'extracting':
        return <Badge variant="secondary"><Loader2 className="w-3 h-3 mr-1 animate-spin" />{t('invoices.import.statusExtracting')}</Badge>
      case 'extracted':
        return <Badge variant="default">{t('invoices.import.statusExtracted')}</Badge>
      case 'extraction_failed':
        return <Badge variant="destructive">{t('invoices.import.statusFailed')}</Badge>
      case 'duplicate':
        return <Badge variant="outline" className="text-orange-600 border-orange-600">{t('invoices.import.statusDuplicate')}</Badge>
      case 'confirmed':
        return <Badge variant="default" className="bg-green-500">{t('invoices.import.statusConfirmed')}</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const getPaymentBadge = (invoice: ImportedInvoice) => {
    if (invoice.isPaid) {
      return <Badge variant="default" className="bg-green-500"><Check className="w-3 h-3 mr-1" />{t('invoices.import.paid')}</Badge>
    }
    return <Badge variant="outline">{t('invoices.import.unpaid')}</Badge>
  }

  const getUploadStatusBadge = (invoice: ImportedInvoice) => {
    if (invoice.uploadStatus === 'pending') {
      return <Badge variant="secondary">{t('invoices.import.uploadPending')}</Badge>
    }
    return null
  }

  const canWrite = hasPermission('invoices', 'generate')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{t('invoices.import.title')}</h1>
          <p className="text-sm text-gray-500">{t('invoices.import.subtitle')}</p>
        </div>
        {canWrite && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setCsvUploadOpen(true)}>
              <FileSpreadsheet className="w-4 h-4 mr-2" />
              {t('invoices.import.importCsv')}
            </Button>
            <Button onClick={() => setUploadOpen(true)}>
              <Upload className="w-4 h-4 mr-2" />
              {t('invoices.import.uploadButton')}
            </Button>
          </div>
        )}
      </div>

      {/* Import Batches */}
      {batches.length > 0 && (
        <div className="rounded-lg border bg-gray-50 p-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.importBatches')}</h3>
          <div className="flex flex-wrap gap-2">
            {batches.map((batch) => (
              <div key={batch.id} className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-md border text-sm">
                <FileSpreadsheet className="w-4 h-4 text-gray-400" />
                <span>{batch.name}</span>
                <Badge variant={batch.pendingCount > 0 ? 'secondary' : 'default'} className="text-xs">
                  {batch.totalUploaded}/{batch.totalExpected}
                </Badge>
                {batch.pendingCount > 0 && (
                  <span className="text-xs text-orange-600">
                    ({batch.pendingCount} {t('invoices.import.pendingUploads')})
                  </span>
                )}
                <button
                  onClick={() => setDeleteBatchId(batch.id)}
                  className="ml-1 text-gray-400 hover:text-red-500"
                  title={t('invoices.import.deleteBatchTooltip')}
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value)
              setPage(1)
            }}
            placeholder={t('invoices.import.searchPlaceholder')}
            className="pl-9"
          />
        </div>
        <div className="inline-flex rounded-md border border-input">
          {[
            { value: 'ALL', label: t('invoices.import.filterAll') },
            { value: 'PAID', label: t('invoices.import.filterPaid') },
            { value: 'UNPAID', label: t('invoices.import.filterUnpaid') },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setPaymentStatus(opt.value); setPage(1) }}
              className={cn(
                'px-3 py-1.5 text-sm font-medium transition-colors first:rounded-l-md last:rounded-r-md',
                paymentStatus === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="inline-flex rounded-md border border-input">
          {[
            { value: 'ALL', label: t('invoices.import.filterAll') },
            { value: 'PENDING', label: t('invoices.import.filterPendingUpload') },
            { value: 'UPLOADED', label: t('invoices.import.filterUploaded') },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setUploadStatus(opt.value); setPage(1) }}
              className={cn(
                'px-3 py-1.5 text-sm font-medium transition-colors first:rounded-l-md last:rounded-r-md',
                uploadStatus === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-white">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-gray-50 text-left text-sm font-medium text-gray-600">
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('invoiceNumber')}
              >
                {t('invoices.import.colInvoiceNumber')}
                {getSortIcon('invoiceNumber')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('invoiceDate')}
              >
                {t('invoices.import.colDate')}
                {getSortIcon('invoiceDate')}
              </th>
              <th
                className="px-4 py-3 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('customerName')}
              >
                {t('invoices.import.colCustomer')}
                {getSortIcon('customerName')}
              </th>
              <th
                className="px-4 py-3 text-right cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalAmount')}
              >
                {t('invoices.import.colAmount')}
                {getSortIcon('totalAmount')}
              </th>
              <th className="px-4 py-3">{t('invoices.import.colStatus')}</th>
              <th className="px-4 py-3">{t('invoices.import.colPayment')}</th>
              <th className="px-4 py-3 text-right">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {loading && invoices.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  <Loader2 className="w-6 h-6 mx-auto animate-spin" />
                </td>
              </tr>
            ) : invoices.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  {t('invoices.import.noInvoices')}
                </td>
              </tr>
            ) : (
              invoices.map((invoice) => (
                <tr key={invoice.id} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          {invoice.invoiceNumber || <span className="text-gray-400 italic">{t('invoices.import.noNumber')}</span>}
                          {getUploadStatusBadge(invoice)}
                        </div>
                        <div className="text-xs text-gray-500">{invoice.originalFilename}</div>
                        {invoice.receiverEmails && invoice.receiverEmails.length > 0 && (
                          <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                            <Mail className="w-3 h-3" />
                            {invoice.receiverEmails.slice(0, 2).join(', ')}
                            {invoice.receiverEmails.length > 2 && ` +${invoice.receiverEmails.length - 2}`}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {invoice.invoiceDate ? formatDate(invoice.invoiceDate) : '-'}
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      {invoice.customerId ? (
                        <>
                          <Link
                            to={`/customers/${invoice.customerId}`}
                            className="text-blue-600 hover:text-blue-800 hover:underline"
                          >
                            {invoice.customerDisplayName || invoice.customerName}
                          </Link>
                          <button
                            onClick={() => !invoice.contractId && handleUnlinkCustomer(invoice.id)}
                            className={`ml-2 ${invoice.contractId ? 'text-gray-300 cursor-not-allowed' : 'text-gray-400 hover:text-red-600'}`}
                            title={invoice.contractId ? t('invoices.import.unlinkCustomerDisabled') : t('invoices.import.unlinkCustomer')}
                            disabled={!!invoice.contractId}
                          >
                            <Unlink className="w-3 h-3 inline" />
                          </button>
                        </>
                      ) : invoice.customerName ? (
                        <>
                          {invoice.customerName}
                          <button
                            onClick={() => setCustomerMatchInvoice(invoice)}
                            className="ml-2 text-blue-600 hover:text-blue-800"
                            title={t('invoices.import.linkCustomer')}
                          >
                            <LinkIcon className="w-3 h-3 inline" />
                          </button>
                        </>
                      ) : (
                        <span className="text-gray-400 italic">{t('invoices.import.noCustomer')}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono">
                    {invoice.totalAmount
                      ? `${formatCurrency(parseFloat(invoice.totalAmount))} ${invoice.currency !== 'EUR' ? invoice.currency : ''}`
                      : '-'}
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(invoice)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {getPaymentBadge(invoice)}
                      {invoice.isPaid && invoice.paymentMatches.length > 0 && (
                        <button
                          onClick={() => openPaymentMatchModal(invoice)}
                          className="text-xs text-blue-600 hover:text-blue-800"
                          title={t('invoices.import.viewPaymentMatch')}
                        >
                          ({invoice.paymentMatches.length})
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      {!invoice.isPaid && invoice.extractionStatus !== 'pending' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openPaymentMatchModal(invoice)}
                          title={t('invoices.import.matchPayment')}
                          className="text-blue-600 hover:text-blue-700 hover:bg-blue-50"
                        >
                          <CreditCard className="w-4 h-4" />
                        </Button>
                      )}
                      {invoice.extractionStatus === 'pending' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleExtract(invoice.id)}
                          title={t('invoices.import.extract')}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </Button>
                      )}
                      {invoice.extractionStatus === 'extraction_failed' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleReExtract(invoice.id)}
                          title={t('invoices.import.reExtract')}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </Button>
                      )}
                      {invoice.pdfUrl && (
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                        >
                          <a href={invoice.pdfUrl} target="_blank" rel="noopener noreferrer">
                            <FileText className="w-4 h-4" />
                          </a>
                        </Button>
                      )}
                      {canWrite && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteId(invoice.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {t('common.showingOf', { from: (page - 1) * pageSize + 1, to: Math.min(page * pageSize, totalCount), total: totalCount })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p - 1)}
              disabled={page === 1}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNextPage}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Upload Modal (supports multiple files) */}
      <Dialog open={uploadOpen} onOpenChange={closeBulkUploadModal}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('invoices.import.uploadTitle')}</DialogTitle>
            <DialogDescription>{t('invoices.import.bulkUploadDescription')}</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                uploadFiles.length > 0 ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-blue-500'
              )}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                multiple
                onChange={handleMultiFileSelect}
                className="hidden"
              />
              {uploadFiles.length > 0 ? (
                <div className="text-green-700">
                  <Check className="w-5 h-5 mx-auto mb-2" />
                  <span>{t('invoices.import.filesSelected', { count: uploadFiles.length })}</span>
                </div>
              ) : (
                <div className="text-gray-500">
                  <Upload className="w-8 h-8 mx-auto mb-2" />
                  <p>{t('invoices.import.dropzoneTextMultiple')}</p>
                  <p className="text-xs mt-1">{t('invoices.import.pdfOnly')}</p>
                </div>
              )}
            </div>

            {/* File list with progress */}
            {uploadProgress.length > 0 && (
              <div className="max-h-48 overflow-y-auto space-y-1">
                {uploadProgress.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm py-1 px-2 rounded bg-gray-50">
                    <span className="truncate flex-1">{item.filename}</span>
                    {item.status === 'pending' && <Badge variant="secondary">{t('invoices.import.pending')}</Badge>}
                    {item.status === 'success' && <Badge variant="default" className="bg-green-500">{t('invoices.import.success')}</Badge>}
                    {item.status === 'error' && (
                      <Badge variant="destructive" title={item.error}>{t('invoices.import.failed')}</Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeBulkUploadModal}>
              {uploadProgress.some(p => p.status === 'success') ? t('common.close') : t('common.cancel')}
            </Button>
            {!uploadProgress.some(p => p.status === 'success') && (
              <Button onClick={handleBulkUpload} disabled={uploadFiles.length === 0 || uploading}>
                {uploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Upload className="w-4 h-4 mr-2" />}
                {t('invoices.import.uploadFiles', { count: uploadFiles.length })}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* CSV Upload Modal */}
      <Dialog open={csvUploadOpen} onOpenChange={setCsvUploadOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('invoices.import.csvUploadTitle')}</DialogTitle>
            <DialogDescription>{t('invoices.import.csvUploadDescription')}</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors',
                csvFile ? 'border-green-500 bg-green-50' : 'border-gray-300 hover:border-blue-500'
              )}
              onClick={() => csvInputRef.current?.click()}
            >
              <input
                ref={csvInputRef}
                type="file"
                accept=".csv"
                onChange={handleCsvSelect}
                className="hidden"
              />
              {csvFile ? (
                <div className="flex items-center justify-center gap-2 text-green-700">
                  <Check className="w-5 h-5" />
                  <span>{csvFile.name}</span>
                </div>
              ) : (
                <div className="text-gray-500">
                  <FileSpreadsheet className="w-8 h-8 mx-auto mb-2" />
                  <p>{t('invoices.import.csvDropzoneText')}</p>
                  <p className="text-xs mt-1">{t('invoices.import.csvFormat')}</p>
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setCsvUploadOpen(false); setCsvFile(null) }}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleCsvUpload} disabled={!csvFile || uploading}>
              {uploading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileSpreadsheet className="w-4 h-4 mr-2" />}
              {t('invoices.import.importCsv')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={!!deleteId} onOpenChange={(open: boolean) => !open && setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('invoices.import.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('invoices.import.deleteConfirmation')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Batch Confirmation */}
      <Dialog open={!!deleteBatchId} onOpenChange={(open: boolean) => !open && setDeleteBatchId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('invoices.import.deleteBatchTitle')}</DialogTitle>
            <DialogDescription>
              {t('invoices.import.deleteBatchConfirmation')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteBatchId(null)}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleDeleteBatch}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Customer Match Modal */}
      <Dialog open={!!customerMatchInvoice} onOpenChange={(open: boolean) => {
        if (!open) {
          setCustomerMatchInvoice(null)
          setCustomerSearch('')
        }
      }}>
        <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('invoices.import.matchCustomerTitle')}</DialogTitle>
            <DialogDescription>
              {t('invoices.import.matchCustomerDescription', { name: customerMatchInvoice?.customerName })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {/* Search input */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                value={customerSearch}
                onChange={(e) => setCustomerSearch(e.target.value)}
                placeholder={t('invoices.import.searchCustomers')}
                className="pl-9"
              />
            </div>

            {/* Search results */}
            {debouncedCustomerSearch && debouncedCustomerSearch.length >= 2 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.searchResults')}</h4>
                {loadingCustomerSearch ? (
                  <div className="text-center py-2">
                    <Loader2 className="w-4 h-4 mx-auto animate-spin" />
                  </div>
                ) : customerSearchData?.customers?.items?.length > 0 ? (
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {customerSearchData.customers.items.map((customer: { id: number; name: string; address?: { city?: string | null } | null; hubspotId: string | null }) => (
                      <button
                        key={customer.id}
                        onClick={() => handleConfirmCustomer(customer.id)}
                        className="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 text-left"
                      >
                        <div>
                          <div className="font-medium">{customer.name}</div>
                          <div className="text-xs text-gray-500">
                            CUS-{customer.id}{customer.address?.city && ` · ${customer.address.city}`}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-2">{t('invoices.import.noSearchResults')}</p>
                )}
              </div>
            )}

            {/* Suggested matches */}
            {!debouncedCustomerSearch && (
              <>
                <h4 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.suggestedCustomers')}</h4>
                {loadingCustomerMatches ? (
                  <div className="text-center py-4">
                    <Loader2 className="w-6 h-6 mx-auto animate-spin" />
                  </div>
                ) : customerMatchData?.customerMatchSuggestions?.length > 0 ? (
                  <div className="space-y-2">
                    {(customerMatchData.customerMatchSuggestions as CustomerMatch[]).map((match) => (
                      <button
                        key={match.customerId}
                        onClick={() => handleConfirmCustomer(match.customerId)}
                        className="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 text-left"
                      >
                        <div>
                          <div className="font-medium">{match.customerName}</div>
                          <div className="text-xs text-gray-500">
                            CUS-{match.customerId}{match.city && ` · ${match.city}`}
                          </div>
                        </div>
                        <Badge variant="secondary">
                          {Math.round(parseFloat(match.similarity) * 100)}% match
                        </Badge>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-500">
                    <AlertCircle className="w-8 h-8 mx-auto mb-2" />
                    <p>{t('invoices.import.noCustomerMatches')}</p>
                  </div>
                )}
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setCustomerMatchInvoice(null)
              setCustomerSearch('')
            }}>
              {t('common.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payment Match Modal */}
      <Dialog open={!!paymentMatchInvoice} onOpenChange={(open: boolean) => {
        if (!open) {
          setPaymentMatchInvoice(null)
          setTransactionSearch('')
        }
      }}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{t('invoices.import.matchPaymentTitle')}</DialogTitle>
            <DialogDescription>
              {paymentMatchInvoice && (
                <>
                  {t('invoices.import.matchPaymentDescription', {
                    invoiceNumber: paymentMatchInvoice.invoiceNumber || paymentMatchInvoice.originalFilename,
                    amount: paymentMatchInvoice.totalAmount ? formatCurrency(parseFloat(paymentMatchInvoice.totalAmount)) : '-',
                    customer: paymentMatchInvoice.customerDisplayName || paymentMatchInvoice.customerName || '-',
                  })}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            {/* Existing matches */}
            {paymentMatchInvoice && paymentMatchInvoice.paymentMatches.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.existingMatches')}</h4>
                <div className="space-y-2">
                  {paymentMatchInvoice.paymentMatches.map((match) => (
                    <div
                      key={match.id}
                      className="flex items-center justify-between p-3 rounded-lg border bg-green-50 border-green-200"
                    >
                      <div>
                        <div className="font-medium">{match.counterpartyName}</div>
                        <div className="text-sm text-gray-500">
                          {formatDate(match.transactionDate)} - {formatCurrency(parseFloat(match.transactionAmount))}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">{match.matchType}</Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeletePaymentMatch(match.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          <Unlink className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested matches */}
            {!paymentMatchInvoice?.isPaid && (
              <>
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.suggestedMatches')}</h4>
                  {loadingPaymentMatches ? (
                    <div className="text-center py-4">
                      <Loader2 className="w-6 h-6 mx-auto animate-spin" />
                    </div>
                  ) : (paymentMatchData?.findPaymentMatches as PaymentMatchCandidate[] | undefined)?.length ? (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {(paymentMatchData.findPaymentMatches as PaymentMatchCandidate[]).map((match) => (
                        <button
                          key={match.transactionId}
                          onClick={() => handleCreatePaymentMatch(match.transactionId, match.matchType)}
                          className="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 text-left"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="font-medium">{match.counterpartyName}</div>
                            <div className="text-sm text-gray-500 break-words">
                              {formatDate(match.transactionDate)} - {match.bookingText}
                            </div>
                          </div>
                          <div className="flex flex-col items-end ml-4">
                            <span className="font-mono text-green-600">
                              {formatCurrency(parseFloat(match.amount))}
                            </span>
                            <div className="flex items-center gap-1">
                              <Badge variant="outline" className="text-xs">{match.matchType}</Badge>
                              <span className="text-xs text-gray-400">
                                {Math.round(parseFloat(match.confidence) * 100)}%
                              </span>
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500 text-center py-2">{t('invoices.import.noSuggestedMatches')}</p>
                  )}
                </div>

                {/* Manual search */}
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">{t('invoices.import.manualSearch')}</h4>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <Input
                      value={transactionSearch}
                      onChange={(e) => setTransactionSearch(e.target.value)}
                      placeholder={t('invoices.import.searchTransactions')}
                      className="pl-9"
                    />
                  </div>
                  {loadingTxSearch ? (
                    <div className="text-center py-2">
                      <Loader2 className="w-4 h-4 mx-auto animate-spin" />
                    </div>
                  ) : debouncedTxSearch && (searchTxData?.bankTransactions?.items as SearchTransaction[] | undefined)?.length ? (
                    <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                      {(searchTxData.bankTransactions.items as SearchTransaction[]).map((tx) => (
                        <button
                          key={tx.id}
                          onClick={() => handleCreatePaymentMatch(tx.id, 'manual')}
                          className="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 text-left"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="font-medium">{tx.counterparty?.name || '-'}</div>
                            <div className="text-sm text-gray-500 break-words">
                              {formatDate(tx.entryDate)} - {tx.bookingText}
                            </div>
                          </div>
                          <span className="font-mono text-green-600 ml-4">
                            {formatCurrency(parseFloat(tx.amount))}
                          </span>
                        </button>
                      ))}
                    </div>
                  ) : debouncedTxSearch ? (
                    <p className="text-sm text-gray-500 text-center py-2 mt-2">{t('invoices.import.noTransactionsFound')}</p>
                  ) : null}
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => {
              setPaymentMatchInvoice(null)
              setTransactionSearch('')
            }}>
              {t('common.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
