import { useState, useRef, useCallback, useEffect } from 'react'
import { usePersistedState } from '@/lib/usePersistedState'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
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
  Eye,
  FileSpreadsheet,
  Mail,
  X,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  FileDown,
  Info,
  Bell,
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
import { HelpVideoButton } from '@/components/HelpVideoButton'
import { CustomerPickerDialog } from '@/components/CustomerPickerDialog'
import { PaymentMatchModal } from './PaymentMatchModal'
import { InvoiceStatusBadge } from '@/components/InvoiceStatusBadge'
import { ReminderDialog } from '@/features/reminders/ReminderDialog'
import { DUNNING_SETTINGS_QUERY, type DunningSettings } from '@/features/reminders/dunning'

// --- GraphQL ---

const INVOICES = gql`
  query Invoices(
    $search: String
    $paymentStatus: PaymentStatusFilter
    $uploadStatus: UploadStatusFilter
    $sortBy: String
    $sortOrder: String
    $offset: Int
    $limit: Int
  ) {
    invoices(
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
  mutation DeleteInvoice($id: ID!) {
    deleteInvoice(id: $id) {
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

const INVOICE_RECORDS = gql`
  query InvoiceRecords(
    $search: String
    $sortBy: String
    $sortOrder: String
    $offset: Int
    $limit: Int
  ) {
    invoiceRecords(
      search: $search
      sortBy: $sortBy
      sortOrder: $sortOrder
      offset: $offset
      limit: $limit
    ) {
      items {
        id
        invoiceNumber
        contractId
        contractName
        customerId
        customerName
        billingDate
        invoiceDate
        totalGross
        status
        generatedAt
        pdfUrl
        isPaid
        emailSentAt
        emailSentTo
        documentType
        dueDate
        overdueDays
        paymentMatches {
          id
          transactionId
          transactionDate
          transactionAmount
          counterpartyName
          matchType
          confidence
        }
      }
      totalCount
      hasNextPage
    }
  }
`


const M365_SETTINGS_QUERY = gql`
  query M365SettingsForInvoices {
    m365Settings {
      isConfigured
      senderMailbox
    }
  }
`

const SEND_INVOICE_EMAIL = gql`
  mutation SendInvoiceEmail($invoiceRecordId: ID!) {
    sendInvoiceEmail(invoiceRecordId: $invoiceRecordId) {
      success
      error
    }
  }
`

const SEND_ALL_UNSENT = gql`
  mutation SendAllUnsentInvoices {
    sendAllUnsentInvoices {
      success
      error
      sent
      errors {
        invoiceNumber
        error
      }
    }
  }
`

interface GeneratedInvoice {
  id: number
  invoiceNumber: string
  contractId: number | null
  contractName: string
  customerId: number | null
  customerName: string
  billingDate: string
  invoiceDate: string | null
  totalGross: string
  status: string
  generatedAt: string
  pdfUrl: string | null
  isPaid: boolean
  emailSentAt: string | null
  emailSentTo: string[]
  documentType: string
  dueDate: string | null
  overdueDays: number
  paymentMatches: {
    id: number
    transactionId: number
    transactionDate: string
    transactionAmount: string
    counterpartyName: string
    matchType: string
    confidence: string
  }[]
}

type SourceFilter = 'ALL' | 'IMPORTED' | 'GENERATED'

interface UnifiedRow {
  key: string
  source: 'imported' | 'generated'
  invoiceNumber: string
  date: string | null
  customerName: string
  customerId: number | null
  contractId: number | null
  contractName?: string
  amount: number | null
  currency: string
  overdueDays: number
  imported?: Invoice
  generated?: GeneratedInvoice
}

interface InvoiceImportBatch {
  id: string
  name: string
  totalExpected: number
  totalUploaded: number
  pendingCount: number
  createdAt: string
  createdByName: string | null
}

interface Invoice {
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

export function InvoiceList() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  // State
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = usePersistedState<SourceFilter>('cm:invoiceList:sourceFilter', 'ALL')
  const [paymentStatus, setPaymentStatus] = usePersistedState<string>('cm:invoiceList:paymentStatus', 'ALL')
  const [uploadStatus, setUploadStatus] = useState<string>('ALL')
  const [page, setPage] = useState(1)
  const [sortField, setSortField] = usePersistedState<string | null>('cm:invoiceList:sortField', null)
  const [sortOrder, setSortOrder] = usePersistedState<'asc' | 'desc'>('cm:invoiceList:sortOrder', 'desc')
  const pageSize = 20

  // Modals
  const [showInfoModal, setShowInfoModal] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [csvUploadOpen, setCsvUploadOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteBatchId, setDeleteBatchId] = useState<string | null>(null)
  const [customerMatchInvoice, setCustomerMatchInvoice] = useState<Invoice | null>(null)
  const [paymentMatchInvoice, setPaymentMatchInvoice] = useState<Invoice | null>(null)
  const [paymentMatchRecord, setPaymentMatchRecord] = useState<GeneratedInvoice | null>(null)

  // File upload
  const fileInputRef = useRef<HTMLInputElement>(null)
  const csvInputRef = useRef<HTMLInputElement>(null)
  const [uploadFiles, setUploadFiles] = useState<File[]>([])
  const [csvFile, setCsvFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{ filename: string; status: 'pending' | 'success' | 'error'; error?: string }[]>([])

  // Queries & Mutations
  const { data, loading, refetch, startPolling, stopPolling } = useQuery(INVOICES, {
    variables: {
      search: search || null,
      paymentStatus: paymentStatus === 'ALL' ? null : paymentStatus,
      uploadStatus: uploadStatus === 'ALL' ? null : uploadStatus,
      sortBy: sortField,
      sortOrder: sortField ? sortOrder : null,
      offset: sourceFilter === 'ALL' ? 0 : (page - 1) * pageSize,
      limit: sourceFilter === 'ALL' ? 1000 : pageSize,
    },
    fetchPolicy: 'cache-and-network',
  })

  const { data: generatedData, loading: generatedLoading, refetch: generatedRefetch } = useQuery(INVOICE_RECORDS, {
    variables: {
      search: search || null,
      sortBy: sortField,
      sortOrder: sortField ? sortOrder : null,
      offset: 0,
      limit: 1000,
    },
    skip: sourceFilter === 'IMPORTED',
    fetchPolicy: 'cache-and-network',
  })

  // Poll for updates when any invoice is being extracted
  useEffect(() => {
    const items = data?.invoices?.items || []
    const hasExtracting = items.some(
      (inv: Invoice) => inv.extractionStatus === 'extracting'
    )

    if (hasExtracting) {
      startPolling(2000) // Poll every 2 seconds
    } else {
      stopPolling()
    }

    return () => stopPolling()
  }, [data?.invoices?.items, startPolling, stopPolling])

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
  const { data: m365Data } = useQuery(M365_SETTINGS_QUERY)
  const [sendInvoiceEmail, { loading: sendingEmail }] = useMutation(SEND_INVOICE_EMAIL)
  const [sendAllUnsent, { loading: sendingAll }] = useMutation(SEND_ALL_UNSENT)
  const [bulkSendErrors, setBulkSendErrors] = useState<{ invoiceNumber: string; error: string }[]>([])
  const [bulkSendSent, setBulkSendSent] = useState<number | null>(null)

  const { data: customerMatchData, loading: loadingCustomerMatches } = useQuery(
    CUSTOMER_MATCH_SUGGESTIONS,
    {
      variables: { invoiceId: customerMatchInvoice?.id },
      skip: !customerMatchInvoice,
    }
  )

  // Dunning settings (for overdue thresholds + reminder action)
  const { data: dunningData } = useQuery<{ dunningSettings: DunningSettings | null }>(
    DUNNING_SETTINGS_QUERY
  )
  const dunningSettings = dunningData?.dunningSettings ?? null
  const [reminderInvoiceId, setReminderInvoiceId] = useState<number | null>(null)


  const invoices: Invoice[] = data?.invoices?.items ?? []
  const generatedInvoices: GeneratedInvoice[] = generatedData?.invoiceRecords?.items ?? []

  // ImportedInvoiceType has no due_date field server-side. Derive overdue
  // days from invoice_date + tenant default payment term so the Verzug
  // column is populated for imported invoices too, not only generated
  // ones. Matches the server-side formula for InvoiceRecord.
  const computeImportedOverdueDays = (
    invoiceDate: string | null,
    isPaid: boolean,
  ): number => {
    if (!invoiceDate || isPaid || !dunningSettings) return 0
    const due = new Date(invoiceDate)
    if (Number.isNaN(due.getTime())) return 0
    due.setDate(due.getDate() + dunningSettings.defaultPaymentTermDays)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    due.setHours(0, 0, 0, 0)
    const diffDays = Math.floor(
      (today.getTime() - due.getTime()) / (1000 * 60 * 60 * 24),
    )
    return diffDays > 0 ? diffDays : 0
  }
  const batches: InvoiceImportBatch[] = batchData?.importBatches?.items ?? []
  const hasPendingUploads = batches.some((b) => b.pendingCount > 0)
  const unsentCount = generatedInvoices.filter(
    inv => inv.status === 'finalized' && !inv.emailSentAt && inv.pdfUrl
  ).length

  // Build unified rows
  const unifiedRows: UnifiedRow[] = (() => {
    const rows: UnifiedRow[] = []

    if (sourceFilter !== 'GENERATED') {
      for (const inv of invoices) {
        rows.push({
          key: `imp-${inv.id}`,
          source: 'imported',
          invoiceNumber: inv.invoiceNumber,
          date: inv.invoiceDate,
          customerName: inv.customerDisplayName || inv.customerName,
          customerId: inv.customerId,
          contractId: inv.contractId,
          amount: inv.totalAmount ? parseFloat(inv.totalAmount) : null,
          currency: inv.currency,
          overdueDays: computeImportedOverdueDays(inv.invoiceDate, inv.isPaid),
          imported: inv,
        })
      }
    }

    if (sourceFilter !== 'IMPORTED') {
      for (const rec of generatedInvoices) {
        // Apply payment status filter client-side for generated invoices
        // Voided invoices are neither paid nor unpaid
        if (paymentStatus === 'PAID' && (!rec.isPaid || rec.status === 'voided')) continue
        if (paymentStatus === 'UNPAID' && (rec.isPaid || rec.status === 'voided')) continue
        rows.push({
          key: `gen-${rec.id}`,
          source: 'generated',
          invoiceNumber: rec.invoiceNumber,
          date: rec.invoiceDate || rec.billingDate,
          customerName: rec.customerName,
          customerId: rec.customerId,
          contractId: rec.contractId,
          contractName: rec.contractName,
          amount: rec.totalGross ? parseFloat(rec.totalGross) : null,
          currency: 'EUR',
          overdueDays: rec.overdueDays ?? 0,
          generated: rec,
        })
      }
    }

    // Sort by date descending when no explicit sort
    if (!sortField) {
      rows.sort((a, b) => {
        const da = a.date || ''
        const db = b.date || ''
        return db.localeCompare(da)
      })
    }

    return rows
  })()

  // Client-side pagination over unified rows
  // When sourceFilter is ALL or GENERATED, both sources are fetched with a fixed limit
  // and merged client-side, so totalCount must reflect actual fetched rows, not server totals.
  const totalCount = sourceFilter === 'IMPORTED'
    ? (data?.invoices?.totalCount ?? 0)
    : unifiedRows.length
  const paginatedRows = sourceFilter === 'ALL'
    ? unifiedRows.slice((page - 1) * pageSize, page * pageSize)
    : unifiedRows
  const totalPages = Math.ceil(totalCount / pageSize)
  const hasNextPage = sourceFilter === 'ALL'
    ? page * pageSize < totalCount
    : (sourceFilter === 'IMPORTED'
      ? (data?.invoices?.hasNextPage ?? false)
      : page * pageSize < totalCount)
  const displayRows = sourceFilter === 'ALL' ? paginatedRows : unifiedRows
  const isLoading = loading || (sourceFilter !== 'IMPORTED' && generatedLoading)

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

  const openPdfWithAuth = async (url: string) => {
    const token = localStorage.getItem('auth_token')
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) return
    const blob = await response.blob()
    const blobUrl = window.URL.createObjectURL(blob)
    window.open(blobUrl, '_blank')
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

  const openPaymentMatchModal = (invoice: Invoice) => {
    setPaymentMatchInvoice(invoice)
    setPaymentMatchRecord(null)
  }

  const handleSendEmail = async (record: GeneratedInvoice) => {
    if (!window.confirm(t('invoices.sendEmailConfirm', { invoice: record.invoiceNumber }))) {
      return
    }
    try {
      const result = await sendInvoiceEmail({
        variables: { invoiceRecordId: String(record.id) },
      })
      if (result.data?.sendInvoiceEmail?.success) {
        generatedRefetch()
      } else {
        window.alert(result.data?.sendInvoiceEmail?.error || t('invoices.sendEmailFailed'))
      }
    } catch {
      window.alert(t('invoices.sendEmailFailed'))
    }
  }

  const handleSendAllUnsent = async () => {
    setBulkSendErrors([])
    setBulkSendSent(null)
    if (!window.confirm(t('invoices.sendAllUnsentConfirm', { count: unsentCount }))) {
      return
    }
    try {
      const result = await sendAllUnsent()
      const data = result.data?.sendAllUnsentInvoices
      if (data?.success) {
        setBulkSendSent(data.sent)
        if (data.errors?.length) {
          setBulkSendErrors(data.errors)
        }
        generatedRefetch()
      } else {
        window.alert(data?.error || t('invoices.sendEmailFailed'))
      }
    } catch {
      window.alert(t('invoices.sendEmailFailed'))
    }
  }

  const openPaymentMatchRecordModal = (record: GeneratedInvoice) => {
    setPaymentMatchRecord(record)
    setPaymentMatchInvoice(null)
  }

  const getUploadStatusBadge = (invoice: Invoice) => {
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
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setShowInfoModal(true)}
            title={t('invoices.import.infoButton')}
          >
            <Info className="w-4 h-4" />
          </Button>
          <HelpVideoButton />
          {canWrite && (
            <>
              <Button variant="outline" onClick={() => setUploadOpen(true)}>
                <Upload className="w-4 h-4 mr-2" />
                {t('invoices.import.uploadButton')}
              </Button>
              <Button variant="outline" onClick={() => setCsvUploadOpen(true)}>
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                {t('invoices.import.importCsv')}
              </Button>
            </>
          )}
          {m365Data?.m365Settings?.isConfigured && unsentCount > 0 && canWrite && (
            <Button
              variant="outline"
              onClick={handleSendAllUnsent}
              disabled={sendingAll}
            >
              {sendingAll ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Mail className="w-4 h-4 mr-2" />
              )}
              {t('invoices.sendAllUnsent', { count: unsentCount })}
            </Button>
          )}
          {hasPermission('invoices', 'export') && (
            <Button className="bg-blue-600 hover:bg-blue-700 text-white" asChild>
              <Link to="/invoices/export">
                <FileDown className="w-4 h-4 mr-2" />
                {t('invoices.generateButton')}
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* Bulk send result */}
      {bulkSendSent !== null && (
        <div className={cn(
          "rounded-lg border p-3 flex items-start gap-3",
          bulkSendErrors.length > 0 ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"
        )}>
          <div className="flex-1">
            <p className={cn("text-sm font-medium", bulkSendErrors.length > 0 ? "text-red-800" : "text-green-800")}>
              {t('invoices.sendAllResult', { sent: bulkSendSent })}
            </p>
            {bulkSendErrors.length > 0 && (
              <div className="mt-1 space-y-0.5">
                {bulkSendErrors.map((err, i) => (
                  <p key={i} className="text-sm text-red-600 flex items-center gap-1">
                    <Mail className="w-3 h-3 text-red-500 shrink-0" />
                    {err.invoiceNumber}: {err.error}
                  </p>
                ))}
              </div>
            )}
          </div>
          <button onClick={() => { setBulkSendSent(null); setBulkSendErrors([]) }} className="text-gray-400 hover:text-gray-600">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

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
      <div className="flex gap-4 flex-wrap">
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
        {/* Source filter */}
        <div className="inline-flex rounded-md border border-input">
          {([
            { value: 'ALL', label: t('invoices.import.sourceAll') },
            { value: 'IMPORTED', label: t('invoices.import.sourceImported') },
            { value: 'GENERATED', label: t('invoices.import.sourceGenerated') },
          ] as const).map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setSourceFilter(opt.value as SourceFilter); setPage(1); setPaymentStatus('ALL'); setUploadStatus('ALL') }}
              className={cn(
                'px-3 py-1.5 text-sm font-medium transition-colors first:rounded-l-md last:rounded-r-md',
                sourceFilter === opt.value
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {/* Payment status filter */}
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
        {/* Upload status filter - only for imported with pending batches */}
        {sourceFilter !== 'GENERATED' && hasPendingUploads && (
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
        )}
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
                onClick={() => handleSort(sourceFilter === 'GENERATED' ? 'totalGross' : 'totalAmount')}
              >
                {t('invoices.import.colAmount')}
                {getSortIcon(sourceFilter === 'GENERATED' ? 'totalGross' : 'totalAmount')}
              </th>
              <th
                className="px-4 py-3 text-right cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('overdueDays')}
                data-testid="invoice-overdue-header"
              >
                {t('reminders.overdueColumn')}
                {getSortIcon('overdueDays')}
              </th>
              {sourceFilter === 'ALL' && (
                <th className="px-4 py-3">{t('invoices.import.source')}</th>
              )}
              <th className="px-4 py-3">{t('invoices.import.colStatus')}</th>
              <th className="px-4 py-3 text-right">{t('common.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && displayRows.length === 0 ? (
              <tr>
                <td colSpan={sourceFilter === 'ALL' ? 8 : 7} className="px-4 py-8 text-center text-gray-500">
                  <Loader2 className="w-6 h-6 mx-auto animate-spin" />
                </td>
              </tr>
            ) : displayRows.length === 0 ? (
              <tr>
                <td colSpan={sourceFilter === 'ALL' ? 8 : 7} className="px-4 py-8 text-center text-gray-500">
                  {t('invoices.import.noInvoicesUnified')}
                </td>
              </tr>
            ) : (
              displayRows.map((row) => (
                <tr key={row.key} className="border-b last:border-0 hover:bg-gray-50">
                  {/* Invoice Number */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      <div>
                        <div className="font-medium flex items-center gap-2">
                          {row.generated ? (
                            <Link to={`/invoices/${row.generated.id}`} className="text-blue-600 hover:underline">
                              {row.invoiceNumber || <span className="text-gray-400 italic">{t('invoices.import.noNumber')}</span>}
                            </Link>
                          ) : row.imported ? (
                            <Link to={`/invoices/${row.imported.id}?type=imported`} className="text-blue-600 hover:underline">
                              {row.invoiceNumber || <span className="text-gray-400 italic">{t('invoices.import.noNumber')}</span>}
                            </Link>
                          ) : (
                            row.invoiceNumber || <span className="text-gray-400 italic">{t('invoices.import.noNumber')}</span>
                          )}
                          {row.generated?.documentType === 'storno' && (
                            <Badge variant="outline" className="text-orange-600 border-orange-300 text-xs">{t('invoices.stornoBadge')}</Badge>
                          )}
                          {row.imported && getUploadStatusBadge(row.imported)}
                        </div>
                        {row.imported && (
                          <div className="text-xs text-gray-500">{row.imported.originalFilename}</div>
                        )}
                        {row.generated && row.contractName && (
                          <Link
                            to={`/contracts/${row.contractId}`}
                            className="text-xs text-gray-500 hover:text-blue-600 hover:underline"
                          >
                            {row.contractName}
                          </Link>
                        )}
                        {row.imported?.receiverEmails && row.imported.receiverEmails.length > 0 && (
                          <div className="flex items-center gap-1 text-xs text-gray-400 mt-0.5">
                            <Mail className="w-3 h-3" />
                            {row.imported.receiverEmails.slice(0, 2).join(', ')}
                            {row.imported.receiverEmails.length > 2 && ` +${row.imported.receiverEmails.length - 2}`}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  {/* Date */}
                  <td className="px-4 py-3">
                    {row.date ? formatDate(row.date) : '-'}
                  </td>
                  {/* Customer */}
                  <td className="px-4 py-3">
                    <div>
                      {row.source === 'imported' && row.imported ? (
                        <>
                          {row.imported.customerId ? (
                            <>
                              <Link
                                to={`/customers/${row.imported.customerId}`}
                                className="text-blue-600 hover:text-blue-800 hover:underline"
                              >
                                {row.imported.customerDisplayName || row.imported.customerName}
                              </Link>
                              <button
                                onClick={() => !row.imported!.contractId && handleUnlinkCustomer(row.imported!.id)}
                                className={`ml-2 ${row.imported.contractId ? 'text-gray-300 cursor-not-allowed' : 'text-gray-400 hover:text-red-600'}`}
                                title={row.imported.contractId ? t('invoices.import.unlinkCustomerDisabled') : t('invoices.import.unlinkCustomer')}
                                disabled={!!row.imported.contractId}
                              >
                                <Unlink className="w-3 h-3 inline" />
                              </button>
                            </>
                          ) : row.imported.customerName ? (
                            <>
                              {row.imported.customerName}
                              <button
                                onClick={() => setCustomerMatchInvoice(row.imported!)}
                                className="ml-2 text-blue-600 hover:text-blue-800"
                                title={t('invoices.import.linkCustomer')}
                              >
                                <LinkIcon className="w-3 h-3 inline" />
                              </button>
                            </>
                          ) : (
                            <span className="text-gray-400 italic">{t('invoices.import.noCustomer')}</span>
                          )}
                        </>
                      ) : row.customerId ? (
                        <Link
                          to={`/customers/${row.customerId}`}
                          className="text-blue-600 hover:text-blue-800 hover:underline"
                        >
                          {row.customerName}
                        </Link>
                      ) : (
                        row.customerName || <span className="text-gray-400 italic">-</span>
                      )}
                    </div>
                  </td>
                  {/* Amount */}
                  <td className="px-4 py-3 text-right font-mono">
                    {row.amount != null
                      ? `${formatCurrency(row.amount)} ${row.currency !== 'EUR' ? row.currency : ''}`
                      : '-'}
                  </td>
                  {/* Overdue days */}
                  <td
                    className="px-4 py-3 text-right font-mono"
                    data-testid={`invoice-overdue-${row.generated ? row.generated.id : row.imported?.id}`}
                  >
                    {row.overdueDays > 0 ? (
                      <span
                        className={cn(
                          dunningSettings &&
                            row.overdueDays >= dunningSettings.overdueRedThresholdDays
                            ? 'font-semibold text-red-600'
                            : 'text-gray-700'
                        )}
                      >
                        {row.overdueDays}
                      </span>
                    ) : (
                      <span className="text-gray-400">–</span>
                    )}
                  </td>
                  {/* Source badge */}
                  {sourceFilter === 'ALL' && (
                    <td className="px-4 py-3">
                      {row.source === 'imported' ? (
                        <Badge variant="outline" className="text-xs">{t('invoices.import.sourceImported')}</Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">{t('invoices.import.sourceGenerated')}</Badge>
                      )}
                    </td>
                  )}
                  {/* Payment */}
                  <td className="px-4 py-3">
                    {row.source === 'imported' && row.imported ? (
                      <div className="flex items-center gap-2">
                        <InvoiceStatusBadge isPaid={row.imported.isPaid} />
                        {row.imported.isPaid && row.imported.paymentMatches.length > 0 && (
                          <button
                            onClick={() => openPaymentMatchModal(row.imported!)}
                            className="text-xs text-blue-600 hover:text-blue-800"
                            title={t('invoices.import.viewPaymentMatch')}
                          >
                            ({row.imported.paymentMatches.length})
                          </button>
                        )}
                      </div>
                    ) : row.source === 'generated' && row.generated ? (
                      <div className="flex items-center gap-2">
                        <InvoiceStatusBadge status={row.generated.status} isPaid={row.generated.isPaid} />
                        {row.generated.isPaid && row.generated.paymentMatches.length > 0 && (
                          <button
                            onClick={() => openPaymentMatchRecordModal(row.generated!)}
                            className="text-xs text-blue-600 hover:text-blue-800"
                            title={t('invoices.import.viewPaymentMatch')}
                          >
                            ({row.generated.paymentMatches.length})
                          </button>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      {row.source === 'imported' && row.imported ? (
                        <>
                          {!row.imported.isPaid && row.imported.extractionStatus !== 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openPaymentMatchModal(row.imported!)}
                              title={t('invoices.import.matchPayment')}
                              className="text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                            >
                              <CreditCard className="w-4 h-4" />
                            </Button>
                          )}
                          {row.imported.extractionStatus === 'pending' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleExtract(row.imported!.id)}
                              title={t('invoices.import.extract')}
                              className="text-gray-400 hover:text-foreground"
                            >
                              <RefreshCw className="w-4 h-4" />
                            </Button>
                          )}
                          {row.imported.extractionStatus === 'extraction_failed' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleReExtract(row.imported!.id)}
                              title={t('invoices.import.reExtract')}
                              className="text-gray-400 hover:text-foreground"
                            >
                              <RefreshCw className="w-4 h-4" />
                            </Button>
                          )}
                          {row.imported.pdfUrl && (
                            <Button
                              variant="ghost"
                              size="sm"
                              asChild
                              className="text-gray-400 hover:text-foreground"
                            >
                              <a href={row.imported.pdfUrl} target="_blank" rel="noopener noreferrer" title={t('invoices.import.viewPdf')}>
                                <Eye className="w-4 h-4" />
                              </a>
                            </Button>
                          )}
                          {canWrite && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => setDeleteId(row.imported!.id)}
                              className="text-gray-400 hover:text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </>
                      ) : row.generated ? (
                        <>
                          {/* Send email button */}
                          {m365Data?.m365Settings?.isConfigured &&
                           row.generated.status === 'finalized' &&
                           !row.generated.emailSentAt &&
                           row.generated.pdfUrl && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleSendEmail(row.generated!)}
                              disabled={sendingEmail}
                              title={t('invoices.sendEmail')}
                              className="text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                            >
                              <Mail className="w-4 h-4" />
                            </Button>
                          )}
                          {/* Sent indicator */}
                          {row.generated.emailSentAt && (
                            <span className="text-xs text-green-600 flex items-center gap-1" title={row.generated.emailSentTo.join(', ')}>
                              <Mail className="w-3 h-3" />
                              {formatDate(row.generated.emailSentAt)}
                            </span>
                          )}
                          {!row.generated.isPaid && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openPaymentMatchRecordModal(row.generated!)}
                              title={t('invoices.import.matchPayment')}
                              className="text-gray-400 hover:text-blue-600 hover:bg-blue-50"
                            >
                              <CreditCard className="w-4 h-4" />
                            </Button>
                          )}
                          {/* Mahnen / send payment reminder */}
                          {!row.generated.isPaid &&
                            row.generated.status !== 'voided' &&
                            hasPermission('reminders', 'send') &&
                            dunningSettings &&
                            row.overdueDays >= dunningSettings.mahnfaehigThresholdDays && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setReminderInvoiceId(row.generated!.id)}
                                title={t('reminders.dunButton')}
                                className="text-gray-400 hover:text-orange-600 hover:bg-orange-50"
                                data-testid={`invoice-dun-${row.generated.id}`}
                              >
                                <Bell className="w-4 h-4" />
                              </Button>
                            )}
                          {row.generated.pdfUrl ? (
                            <Button variant="ghost" size="sm" asChild className="text-gray-400 hover:text-foreground">
                              <a href={row.generated.pdfUrl} target="_blank" rel="noopener noreferrer" title={t('invoices.import.viewPdf')}>
                                <Eye className="w-4 h-4" />
                              </a>
                            </Button>
                          ) : (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-gray-400 hover:text-foreground"
                              onClick={() => openPdfWithAuth(`/api/invoices/${row.generated!.id}/pdf/`)}
                              title={t('invoices.import.viewPdf')}
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          )}
                          {row.contractId && (
                            <Button
                              variant="ghost"
                              size="sm"
                              asChild
                              className="text-gray-400 hover:text-foreground"
                            >
                              <Link to={`/contracts/${row.contractId}`} title={t('invoices.import.contractLink')}>
                                <LinkIcon className="w-4 h-4" />
                              </Link>
                            </Button>
                          )}
                        </>
                      ) : null}
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
            {t('common.pagination.showing', {
              from: (page - 1) * pageSize + 1,
              to: Math.min(page * pageSize, totalCount),
              total: totalCount,
            })}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => p - 1)}
              disabled={page === 1}
              className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              {t('common.pagination.previous')}
            </button>
            <span className="text-sm text-gray-500">
              {t('common.pagination.page', { page, totalPages })}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!hasNextPage}
              className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {t('common.pagination.next')}
              <ChevronRight className="h-4 w-4" />
            </button>
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
      <CustomerPickerDialog
        open={!!customerMatchInvoice}
        onOpenChange={(open) => { if (!open) setCustomerMatchInvoice(null) }}
        title={t('invoices.import.matchCustomerTitle')}
        description={t('invoices.import.matchCustomerDescription', { name: customerMatchInvoice?.customerName })}
        onSelect={(customerId) => handleConfirmCustomer(customerId)}
      >
        {/* Suggested matches */}
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
      </CustomerPickerDialog>

      {/* Info Modal */}
      <Dialog open={showInfoModal} onOpenChange={setShowInfoModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('invoices.import.infoTitle')}</DialogTitle>
            <DialogDescription className="sr-only">{t('invoices.import.infoTitle')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-6 text-sm">
            {/* Invoice Types */}
            <div>
              <h3 className="font-semibold text-base mb-2">{t('invoices.import.infoTypesTitle')}</h3>
              <div className="space-y-2">
                <div className="flex gap-3">
                  <Badge variant="outline" className="shrink-0 bg-blue-50 text-blue-700 border-blue-200">{t('invoices.import.sourceGenerated')}</Badge>
                  <p className="text-muted-foreground">{t('invoices.import.infoTypesGenerated')}</p>
                </div>
                <div className="flex gap-3">
                  <Badge variant="outline" className="shrink-0">{t('invoices.import.sourceImported')}</Badge>
                  <p className="text-muted-foreground">{t('invoices.import.infoTypesImported')}</p>
                </div>
              </div>
            </div>

            {/* Generated Statuses */}
            <div>
              <h3 className="font-semibold text-base mb-2">{t('invoices.import.infoGeneratedStatusTitle')}</h3>
              <div className="space-y-2">
                {[
                  { key: 'finalized', label: t('invoices.import.generatedStatus.finalized'), desc: t('invoices.import.infoGeneratedStatusFinalized'), color: 'bg-gray-50 text-gray-600' },
                  { key: 'sent', label: t('invoices.import.generatedStatus.sent'), desc: t('invoices.import.infoGeneratedStatusSent'), color: 'bg-purple-50 text-purple-700' },
                  { key: 'paid', label: t('invoices.import.generatedStatus.paid'), desc: t('invoices.import.infoGeneratedStatusPaid'), color: 'bg-green-100 text-green-800' },
                  { key: 'dunning', label: t('invoices.import.generatedStatus.dunning'), desc: t('invoices.import.infoGeneratedStatusDunning'), color: 'bg-orange-100 text-orange-700' },
                  { key: 'voided', label: t('invoices.import.generatedStatus.voided'), desc: t('invoices.import.infoGeneratedStatusVoided'), color: 'bg-gray-100 text-gray-600' },
                ].map((s) => (
                  <div key={s.key} className="flex gap-3 items-start">
                    <Badge variant="outline" className={cn('shrink-0', s.color)}>{s.label}</Badge>
                    <p className="text-muted-foreground">{s.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Imported Statuses */}
            <div>
              <h3 className="font-semibold text-base mb-2">{t('invoices.import.infoImportedStatusTitle')}</h3>
              <div className="space-y-2">
                {[
                  { key: 'pending', label: t('invoices.import.statusPending'), desc: t('invoices.import.infoImportedStatusPending'), color: 'bg-gray-100 text-gray-700' },
                  { key: 'extracting', label: t('invoices.import.statusExtracting'), desc: t('invoices.import.infoImportedStatusExtracting'), color: 'bg-yellow-100 text-yellow-800' },
                  { key: 'extracted', label: t('invoices.import.statusExtracted'), desc: t('invoices.import.infoImportedStatusExtracted'), color: 'bg-blue-100 text-blue-800' },
                  { key: 'failed', label: t('invoices.import.statusFailed'), desc: t('invoices.import.infoImportedStatusFailed'), color: 'bg-red-100 text-red-800' },
                  { key: 'duplicate', label: t('invoices.import.statusDuplicate'), desc: t('invoices.import.infoImportedStatusDuplicate'), color: 'bg-orange-100 text-orange-800' },
                  { key: 'confirmed', label: t('invoices.import.statusConfirmed'), desc: t('invoices.import.infoImportedStatusConfirmed'), color: 'bg-green-100 text-green-800' },
                  { key: 'sent', label: t('invoices.import.generatedStatus.sent'), desc: t('invoices.import.infoImportedStatusSent'), color: 'bg-green-100 text-green-800' },
                  { key: 'paid', label: t('invoices.import.paid'), desc: t('invoices.import.infoImportedStatusPaid'), color: 'bg-green-100 text-green-800' },
                ].map((s) => (
                  <div key={s.key} className="flex gap-3 items-start">
                    <Badge variant="outline" className={cn('shrink-0', s.color)}>{s.label}</Badge>
                    <p className="text-muted-foreground">{s.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Payment Matching */}
            <div>
              <h3 className="font-semibold text-base mb-2">{t('invoices.import.infoPaymentTitle')}</h3>
              <p className="text-muted-foreground">{t('invoices.import.infoPaymentDescription')}</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Payment Match Modal */}
      <PaymentMatchModal
        open={!!paymentMatchInvoice || !!paymentMatchRecord}
        onOpenChange={(open) => {
          if (!open) {
            setPaymentMatchInvoice(null)
            setPaymentMatchRecord(null)
          }
        }}
        invoiceId={paymentMatchInvoice?.id}
        invoiceRecordId={paymentMatchRecord?.id}
        invoiceNumber={
          paymentMatchInvoice?.invoiceNumber || paymentMatchInvoice?.originalFilename ||
          paymentMatchRecord?.invoiceNumber || ''
        }
        amount={paymentMatchInvoice?.totalAmount || paymentMatchRecord?.totalGross || null}
        customerName={
          paymentMatchInvoice?.customerDisplayName || paymentMatchInvoice?.customerName ||
          paymentMatchRecord?.customerName || ''
        }
        isPaid={paymentMatchInvoice?.isPaid || paymentMatchRecord?.isPaid || false}
        existingMatches={paymentMatchInvoice?.paymentMatches ?? paymentMatchRecord?.paymentMatches ?? []}
        onMatchChanged={() => {
          setPaymentMatchInvoice(null)
          setPaymentMatchRecord(null)
          refetch()
          generatedRefetch()
        }}
      />

      {/* Payment Reminder Dialog */}
      <ReminderDialog
        open={reminderInvoiceId != null}
        onOpenChange={(open) => { if (!open) setReminderInvoiceId(null) }}
        invoiceRecordId={reminderInvoiceId}
        onSent={() => {
          setReminderInvoiceId(null)
          generatedRefetch()
        }}
      />
    </div>
  )
}
