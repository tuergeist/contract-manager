import { useState, useEffect, useRef } from 'react'
import { usePersistedState } from '@/lib/usePersistedState'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  ArrowLeft,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  Pencil,
  Check,
  GitMerge,
  Link as LinkIcon,
  Unlink,
  User,
  Eye,
  Search as SearchIcon,
  Link2 as ChainIcon,
} from 'lucide-react'
import { formatCurrency, formatDate } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Button } from '@/components/ui/button'
import { TransactionMatchSheet } from './TransactionMatchSheet'
import { IncomingInvoiceDetail } from '../incoming-invoices/IncomingInvoiceDetail'
import { Badge } from '@/components/ui/badge'
import { Link2, FileText, Receipt } from 'lucide-react'

const COUNTERPARTY_DETAIL = gql`
  query CounterpartyDetail($id: ID!, $dateFrom: Date, $dateTo: Date) {
    counterparty(id: $id, dateFrom: $dateFrom, dateTo: $dateTo) {
      id
      name
      iban
      bic
      totalDebit
      totalCredit
      transactionCount
      firstDate
      lastDate
      totalInvoiced
      invoiceCount
      customer {
        id
        name
      }
      defaultCostCenter { id code name isActive }
    }
  }
`

const BANK_TRANSACTIONS = gql`
  query BankTransactions(
    $accountId: Int
    $search: String
    $counterpartyId: ID
    $dateFrom: Date
    $dateTo: Date
    $amountMin: Decimal
    $amountMax: Decimal
    $direction: String
    $sortBy: String
    $sortOrder: String
    $page: Int
    $pageSize: Int
  ) {
    bankTransactions(
      accountId: $accountId
      search: $search
      counterpartyId: $counterpartyId
      dateFrom: $dateFrom
      dateTo: $dateTo
      amountMin: $amountMin
      amountMax: $amountMax
      direction: $direction
      sortBy: $sortBy
      sortOrder: $sortOrder
      page: $page
      pageSize: $pageSize
    ) {
      items {
        id
        entryDate
        valueDate
        amount
        currency
        transactionType
        counterparty {
          id
          name
          iban
          bic
        }
        bookingText
        reference
        accountName
        matchedInvoice {
          invoiceId
          invoiceNumber
          invoiceType
        }
      }
      totalCount
      page
      pageSize
      hasNextPage
    }
  }
`

const SEARCH_COUNTERPARTIES = gql`
  query SearchCounterparties($search: String, $page: Int, $pageSize: Int) {
    counterparties(search: $search, page: $page, pageSize: $pageSize) {
      items {
        id
        name
        transactionCount
      }
    }
  }
`

const UPDATE_COUNTERPARTY = gql`
  mutation UpdateCounterparty($input: UpdateCounterpartyInput!) {
    updateCounterparty(input: $input) {
      success
      error
      counterparty {
        id
        name
        iban
        bic
        defaultCostCenter { id code name isActive }
      }
    }
  }
`

const COST_CENTERS_FOR_DROPDOWN = gql`
  query CostCentersForDropdown {
    costCenters(isActive: true) { id code name }
  }
`

const MERGE_COUNTERPARTIES = gql`
  mutation MergeCounterparties($sourceId: ID!, $targetId: ID!) {
    mergeCounterparties(sourceId: $sourceId, targetId: $targetId) {
      success
      error
      mergedTransactionCount
      target {
        id
        name
      }
    }
  }
`

const SEARCH_CUSTOMERS = gql`
  query SearchCustomers($search: String, $isActive: Boolean) {
    customers(search: $search, isActive: $isActive) {
      items {
        id
        name
        netsuiteCustomerNumber
      }
      totalCount
    }
  }
`

const LINK_COUNTERPARTY_TO_CUSTOMER = gql`
  mutation LinkCounterpartyToCustomer($counterpartyId: ID!, $customerId: Int!) {
    linkCounterpartyToCustomer(counterpartyId: $counterpartyId, customerId: $customerId) {
      success
      error
      counterparty {
        id
        customerId
        customerName
      }
    }
  }
`

const UNLINK_COUNTERPARTY_FROM_CUSTOMER = gql`
  mutation UnlinkCounterpartyFromCustomer($counterpartyId: ID!) {
    unlinkCounterpartyFromCustomer(counterpartyId: $counterpartyId) {
      success
      error
      counterparty {
        id
        customerId
        customerName
      }
    }
  }
`

const COUNTERPARTY_INVOICE_YEARS = gql`
  query CounterpartyInvoiceYears($counterpartyId: ID!) {
    incomingInvoices(counterpartyId: $counterpartyId, pageSize: 200) {
      items { invoiceDate }
    }
  }
`

const COUNTERPARTY_INVOICES = gql`
  query CounterpartyInvoices($counterpartyId: ID!, $sortBy: String, $sortOrder: String, $page: Int, $pageSize: Int) {
    incomingInvoices(counterpartyId: $counterpartyId, sortBy: $sortBy, sortOrder: $sortOrder, page: $page, pageSize: $pageSize) {
      items {
        id
        supplierName
        invoiceNumber
        invoiceDate
        grossAmount
        currency
        extractionStatus
        originalFilename
        pdfUrl
      }
      totalCount
      hasNextPage
    }
  }
`

const COUNTERPARTY_OUTGOING_INVOICES = gql`
  query CounterpartyOutgoingInvoices($customerId: Int!, $sortBy: String, $sortOrder: String, $offset: Int, $limit: Int) {
    invoiceRecords(customerId: $customerId, sortBy: $sortBy, sortOrder: $sortOrder, offset: $offset, limit: $limit) {
      items {
        id
        invoiceNumber
        invoiceDate
        totalGross
        status
        isPaid
        pdfUrl
        contractName
        documentType
        stornoOfId
        stornoOfNumber
      }
      totalCount
      hasNextPage
    }
  }
`

const invoiceStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  extracting: 'bg-blue-100 text-blue-800',
  extracted: 'bg-green-100 text-green-800',
  extraction_failed: 'bg-red-100 text-red-800',
  confirmed: 'bg-emerald-100 text-emerald-800',
  matched: 'bg-purple-100 text-purple-800',
}

interface Counterparty {
  id: string
  name: string
  iban: string
  bic: string
}

interface BankTransaction {
  id: number
  entryDate: string
  valueDate: string | null
  amount: string
  currency: string
  transactionType: string
  counterparty: Counterparty
  bookingText: string
  reference: string
  accountName: string
  matchedInvoice: { invoiceId: string; invoiceNumber: string; invoiceType: string } | null
}

interface CounterpartySummary {
  id: string
  name: string
  iban: string
  bic: string
  totalDebit: string
  totalCredit: string
  transactionCount: number
  firstDate: string
  lastDate: string
  totalInvoiced: string
  invoiceCount: number
  customer: { id: number; name: string } | null
  defaultCostCenter: { id: string; code: string; name: string; isActive: boolean } | null
}

interface CustomerSearchResult {
  id: number
  name: string
  netsuiteCustomerNumber: string | null
}

export function CounterpartyDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const cpDateFrom = searchParams.get('dateFrom') || null
  const cpDateTo = searchParams.get('dateTo') || null

  // Summary year filter
  const currentYear = new Date().getFullYear()
  const [summaryYear, setSummaryYear] = useState<string>(String(currentYear))
  const summaryDateFrom = summaryYear === 'total' ? null : `${summaryYear}-01-01`
  const summaryDateTo = summaryYear === 'total' ? null : `${summaryYear}-12-31`

  // Expanded transaction row
  const [expandedTxId, setExpandedTxId] = useState<number | null>(null)

  // Match sheet state
  const [matchSheetTxId, setMatchSheetTxId] = useState<number | null>(null)
  const [matchSheetOpen, setMatchSheetOpen] = useState(false)

  // Rename state
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const editInputRef = useRef<HTMLInputElement>(null)

  // Merge state
  const [mergeDialogOpen, setMergeDialogOpen] = useState(false)
  const [mergeTargetSearch, setMergeTargetSearch] = useState('')
  const [mergeTargetId, setMergeTargetId] = useState<string | null>(null)
  const [mergeTargetName, setMergeTargetName] = useState<string | null>(null)
  const [mergePopoverOpen, setMergePopoverOpen] = useState(false)

  // Customer link state
  const [customerLinkDialogOpen, setCustomerLinkDialogOpen] = useState(false)
  const [customerSearch, setCustomerSearch] = useState('')
  const [debouncedCustomerSearch, setDebouncedCustomerSearch] = useState('')
  const [customerPopoverOpen, setCustomerPopoverOpen] = useState(false)
  const customerSearchInputRef = useRef<HTMLInputElement>(null)

  // Tab state
  const [activeTab, setActiveTab] = useState<'account' | 'transactions' | 'invoices' | 'outgoing'>('account')
  const [invPage, setInvPage] = useState(1)
  const [invSortBy, setInvSortBy] = useState('invoice_date')
  const [invSortOrder, setInvSortOrder] = useState<'asc' | 'desc'>('desc')
  const [outPage, setOutPage] = useState(1)
  const [outSortBy, setOutSortBy] = useState<string>('invoiceDate')
  const [outSortOrder, setOutSortOrder] = useState<'asc' | 'desc'>('desc')
  const [ledgerSortOrder, setLedgerSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedInvId, setSelectedInvId] = useState<string | null>(null)

  // Filters (kept for query variables but no UI)
  const [filterAccountId] = useState<string>('all')
  const [searchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [dateFrom] = useState('')
  const [dateTo] = useState('')
  const [amountMin] = useState('')
  const [amountMax] = useState('')
  const [direction] = useState<string>('all')
  const [sortBy, setSortBy] = usePersistedState('cm:counterpartyDetail:sortBy', 'date')
  const [sortOrder, setSortOrder] = usePersistedState('cm:counterpartyDetail:sortOrder', 'desc')
  const [page, setPage] = useState(1)
  const pageSize = 50

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedCustomerSearch(customerSearch), 300)
    return () => clearTimeout(timer)
  }, [customerSearch])

  useEffect(() => {
    setPage(1)
  }, [filterAccountId, debouncedSearch, dateFrom, dateTo, amountMin, amountMax, direction])

  // Counterparty detail query
  const { data: costCentersData } = useQuery(COST_CENTERS_FOR_DROPDOWN)
  const { data: cpData, loading: cpLoading } = useQuery(COUNTERPARTY_DETAIL, {
    variables: { id, dateFrom: summaryDateFrom || cpDateFrom, dateTo: summaryDateTo || cpDateTo },
    skip: !id,
  })

  // Incoming invoices for this counterparty
  const { data: invData, loading: invLoading } = useQuery(COUNTERPARTY_INVOICES, {
    variables: { counterpartyId: id, sortBy: invSortBy, sortOrder: invSortOrder, page: invPage, pageSize: 50 },
    skip: !id,
  })
  const cpInvoices = invData?.incomingInvoices?.items || []
  const invTotalCount = invData?.incomingInvoices?.totalCount || 0
  const invHasNextPage = invData?.incomingInvoices?.hasNextPage || false

  // Invoice years for year selector
  const { data: invYearsData } = useQuery(COUNTERPARTY_INVOICE_YEARS, {
    variables: { counterpartyId: id },
    skip: !id,
  })

  const summary: CounterpartySummary | null = cpData?.counterparty || null

  // Outgoing invoices for this counterparty (via linked customer)
  const linkedCustomerId = summary?.customer?.id ?? null
  const { data: outData, loading: outLoading } = useQuery(COUNTERPARTY_OUTGOING_INVOICES, {
    variables: {
      customerId: linkedCustomerId,
      sortBy: outSortBy,
      sortOrder: outSortOrder,
      offset: (outPage - 1) * 50,
      limit: 50,
    },
    skip: !linkedCustomerId,
  })
  const outInvoices = outData?.invoiceRecords?.items || []
  const outTotalCount = outData?.invoiceRecords?.totalCount || 0
  const outHasNextPage = outData?.invoiceRecords?.hasNextPage || false
  // Bulk fetch for account ledger (no pagination)
  const { data: outAllData } = useQuery(COUNTERPARTY_OUTGOING_INVOICES, {
    variables: { customerId: linkedCustomerId, sortBy: 'invoiceDate', sortOrder: 'asc', offset: 0, limit: 500 },
    skip: !linkedCustomerId,
  })
  const allOutInvoices = outAllData?.invoiceRecords?.items || []
  // Rule of thumb: if any outgoing invoices exist → counterparty is treated as a Debitor
  // (customer account). Otherwise it's a Kreditor (vendor account). Different Soll/Haben
  // conventions apply per account type.
  const accountType: 'debtor' | 'creditor' = allOutInvoices.length > 0 ? 'debtor' : 'creditor'

  // Transactions query
  const { data: txData, loading: txLoading, refetch: txRefetch } = useQuery(BANK_TRANSACTIONS, {
    variables: {
      accountId: filterAccountId !== 'all' ? parseInt(filterAccountId) : null,
      search: debouncedSearch || null,
      counterpartyId: id,
      dateFrom: dateFrom || null,
      dateTo: dateTo || null,
      amountMin: amountMin ? parseFloat(amountMin) : null,
      amountMax: amountMax ? parseFloat(amountMax) : null,
      direction: direction !== 'all' ? direction : null,
      sortBy,
      sortOrder,
      page,
      pageSize,
    },
    skip: !id,
    fetchPolicy: 'cache-and-network',
  })

  const transactions: BankTransaction[] = txData?.bankTransactions?.items ?? []
  const totalCount = txData?.bankTransactions?.totalCount ?? 0
  const hasNextPage = txData?.bankTransactions?.hasNextPage ?? false
  const totalPages = Math.ceil(totalCount / pageSize)

  // Search counterparties for merge
  const { data: searchData } = useQuery(SEARCH_COUNTERPARTIES, {
    variables: { search: mergeTargetSearch, page: 1, pageSize: 20 },
    skip: !mergeDialogOpen,
  })
  const searchResults = (searchData?.counterparties?.items ?? []).filter(
    (cp: { id: string }) => cp.id !== id // Exclude current counterparty
  )

  // Search customers for linking
  const { data: customerSearchData } = useQuery(SEARCH_CUSTOMERS, {
    variables: { search: debouncedCustomerSearch, isActive: true },
    skip: !customerLinkDialogOpen || !debouncedCustomerSearch,
  })
  const customerResults: CustomerSearchResult[] = customerSearchData?.customers?.items ?? []

  // Mutations
  const [updateCounterparty, { loading: updating }] = useMutation(UPDATE_COUNTERPARTY, {
    refetchQueries: ['CounterpartyDetail'],
  })
  const [mergeCounterparties, { loading: merging }] = useMutation(MERGE_COUNTERPARTIES)
  const [linkCustomer, { loading: linking }] = useMutation(LINK_COUNTERPARTY_TO_CUSTOMER, {
    refetchQueries: ['CounterpartyDetail'],
  })
  const [unlinkCustomer, { loading: unlinking }] = useMutation(UNLINK_COUNTERPARTY_FROM_CUSTOMER, {
    refetchQueries: ['CounterpartyDetail'],
  })

  // Start editing
  const handleStartEdit = () => {
    setEditName(summary?.name ?? '')
    setIsEditing(true)
    setTimeout(() => editInputRef.current?.focus(), 0)
  }

  // Save rename
  const handleSaveRename = async () => {
    if (!editName.trim() || editName === summary?.name) {
      setIsEditing(false)
      return
    }
    try {
      const { data } = await updateCounterparty({
        variables: { input: { id, name: editName.trim() } },
      })
      if (data?.updateCounterparty?.success) {
        setIsEditing(false)
      } else {
        alert(data?.updateCounterparty?.error || 'Failed to rename')
      }
    } catch (err) {
      console.error('Rename error:', err)
      alert('Failed to rename counterparty')
    }
  }

  // Handle merge
  const handleMerge = async () => {
    if (!mergeTargetId) return
    try {
      const { data } = await mergeCounterparties({
        variables: { sourceId: id, targetId: mergeTargetId },
      })
      if (data?.mergeCounterparties?.success) {
        // Navigate to the target counterparty
        navigate(`/banking/counterparty/${mergeTargetId}`)
      } else {
        alert(data?.mergeCounterparties?.error || 'Failed to merge')
      }
    } catch (err) {
      console.error('Merge error:', err)
      alert('Failed to merge counterparties')
    }
  }

  // Handle customer link
  const handleLinkCustomer = async (customerId: number) => {
    if (!id) return
    try {
      const { data } = await linkCustomer({
        variables: { counterpartyId: id, customerId: Number(customerId) },
      })
      if (data?.linkCounterpartyToCustomer?.success) {
        setCustomerLinkDialogOpen(false)
        setCustomerSearch('')
        setCustomerPopoverOpen(false)
      } else {
        alert(data?.linkCounterpartyToCustomer?.error || 'Failed to link customer')
      }
    } catch (err) {
      console.error('Link error:', err)
      alert('Failed to link customer')
    }
  }

  // Handle customer unlink
  const handleUnlinkCustomer = async () => {
    if (!id) return
    try {
      const { data } = await unlinkCustomer({
        variables: { counterpartyId: id },
      })
      if (!data?.unlinkCounterpartyFromCustomer?.success) {
        alert(data?.unlinkCounterpartyFromCustomer?.error || 'Failed to unlink customer')
      }
    } catch (err) {
      console.error('Unlink error:', err)
      alert('Failed to unlink customer')
    }
  }

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  const getSortIcon = (field: string) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />
    return sortOrder === 'asc'
      ? <ArrowUp className="h-3.5 w-3.5" />
      : <ArrowDown className="h-3.5 w-3.5" />
  }

  if (cpLoading && !cpData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!summary && !cpLoading) {
    return (
      <div>
        <button
          onClick={() => navigate('/banking')}
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('banking.backToBanking')}
        </button>
        <p className="text-gray-500">{t('banking.counterpartyNotFound')}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Back button */}
      <button
        onClick={() => navigate('/banking')}
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('banking.backToBanking')}
      </button>

      {/* Page Title with Edit and Merge */}
      <div className="flex items-center gap-3">
        {isEditing ? (
          <div className="flex items-center gap-2">
            <input
              ref={editInputRef}
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveRename()
                if (e.key === 'Escape') setIsEditing(false)
              }}
              className="rounded-md border border-blue-500 px-3 py-1.5 text-2xl font-bold focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleSaveRename}
              disabled={updating}
              className="rounded-md bg-blue-600 p-2 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {updating ? <Loader2 className="h-5 w-5 animate-spin" /> : <Check className="h-5 w-5" />}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="rounded-md border border-gray-300 p-2 text-gray-500 hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <>
            <h1 className="text-2xl font-bold text-gray-900">{summary?.name}</h1>
            <Badge
              variant="secondary"
              className={accountType === 'debtor' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}
              title={accountType === 'debtor' ? t('banking.debtorHint', 'Customer — Soll: outgoing invoice, Haben: payment received') : t('banking.creditorHint', 'Vendor — Haben: incoming invoice, Soll: payment sent')}
            >
              {accountType === 'debtor' ? t('banking.debtor', 'Debitor') : t('banking.creditor', 'Kreditor')}
            </Badge>
            <button
              onClick={handleStartEdit}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title={t('common.rename')}
            >
              <Pencil className="h-4 w-4" />
            </button>
            <button
              onClick={() => setMergeDialogOpen(true)}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title={t('banking.mergeCounterparty')}
            >
              <GitMerge className="h-4 w-4" />
            </button>
            <button
              onClick={() => {
                const firstWord = (summary?.name ?? '').split(/[\s\-_,./]+/)[0] || ''
                setCustomerSearch(firstWord)
                setDebouncedCustomerSearch(firstWord)
                setCustomerLinkDialogOpen(true)
                setCustomerPopoverOpen(true)
              }}
              className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              title={t('banking.linkToCustomer')}
            >
              <LinkIcon className="h-4 w-4" />
            </button>
          </>
        )}
      </div>

      {/* Linked Customer */}
      {summary?.customer && (
        <div className="mt-2 flex items-center gap-2">
          <User className="h-4 w-4 text-blue-600" />
          <Link
            to={`/customers/${summary.customer.id}`}
            className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
          >
            {summary.customer.name}
          </Link>
          <button
            onClick={handleUnlinkCustomer}
            disabled={unlinking}
            className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-600"
            title={t('banking.unlinkCustomer')}
          >
            {unlinking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Unlink className="h-3.5 w-3.5" />}
          </button>
        </div>
      )}

      {/* IBAN/BIC if available */}
      {(summary?.iban || summary?.bic) && (
        <p className="mt-1 text-sm text-gray-500">
          {summary?.iban && <span>{summary.iban}</span>}
          {summary?.iban && summary?.bic && <span> / </span>}
          {summary?.bic && <span>{summary.bic}</span>}
        </p>
      )}

      {/* Default Cost Center */}
      <div className="mt-2 flex items-center gap-2">
        <span className="text-sm text-gray-500">{t('costCenters.defaultCostCenter')}:</span>
        <select
          value={summary?.defaultCostCenter?.id || ''}
          onChange={async (e) => {
            await updateCounterparty({ variables: { input: { id, defaultCostCenterId: e.target.value || null } } })
          }}
          className="rounded-md border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">{t('costCenters.noCostCenter')}</option>
          {(costCentersData?.costCenters || []).map((cc: { id: string; code: string; name: string }) => (
            <option key={cc.id} value={cc.id}>{cc.code} – {cc.name}</option>
          ))}
        </select>
      </div>

      {/* Merge Dialog */}
      <Dialog open={mergeDialogOpen} onOpenChange={setMergeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('banking.mergeCounterparty')}</DialogTitle>
            <DialogDescription>
              {t('banking.mergeDescription', { name: summary?.name })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              {t('banking.mergeTarget')}
            </label>
            <Popover open={mergePopoverOpen} onOpenChange={setMergePopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  className="w-full justify-between"
                >
                  {mergeTargetName || t('banking.selectCounterparty')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder={t('common.search')}
                    value={mergeTargetSearch}
                    onValueChange={setMergeTargetSearch}
                  />
                  <CommandList>
                    <CommandEmpty>{t('banking.noCounterpartiesFound')}</CommandEmpty>
                    {searchResults.map((cp: { id: string; name: string; transactionCount: number }) => (
                      <CommandItem
                        key={cp.id}
                        value={cp.id}
                        onSelect={() => {
                          setMergeTargetId(cp.id)
                          setMergeTargetName(cp.name)
                          setMergePopoverOpen(false)
                        }}
                      >
                        <div className="flex w-full items-center justify-between">
                          <span>{cp.name}</span>
                          <span className="text-xs text-gray-400">
                            {t('banking.transactionCount', { count: cp.transactionCount })}
                          </span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setMergeDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleMerge}
              disabled={!mergeTargetId || merging}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {merging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('banking.merge')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Customer Link Dialog */}
      <Dialog open={customerLinkDialogOpen} onOpenChange={(open) => {
        setCustomerLinkDialogOpen(open)
        if (!open) {
          setCustomerSearch('')
          setCustomerPopoverOpen(false)
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('banking.linkToCustomer')}</DialogTitle>
            <DialogDescription>
              {t('banking.linkCustomerDescription', { name: summary?.name })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="mb-2 block text-sm font-medium text-gray-700">
              {t('banking.selectCustomerToLink')}
            </label>
            <Popover open={customerPopoverOpen} onOpenChange={setCustomerPopoverOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  className="w-full justify-between"
                >
                  {t('banking.searchCustomers')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start"
                onOpenAutoFocus={(e) => {
                  e.preventDefault()
                  setTimeout(() => customerSearchInputRef.current?.focus(), 0)
                }}
              >
                <Command shouldFilter={false}>
                  <CommandInput
                    ref={customerSearchInputRef}
                    placeholder={t('common.search')}
                    value={customerSearch}
                    onValueChange={setCustomerSearch}
                  />
                  <CommandList>
                    <CommandEmpty>{t('banking.noCustomersFound')}</CommandEmpty>
                    {customerResults.map((customer) => (
                      <CommandItem
                        key={customer.id}
                        value={String(customer.id)}
                        onSelect={() => handleLinkCustomer(customer.id)}
                        disabled={linking}
                      >
                        <div className="flex w-full items-center">
                          <User className="mr-2 h-4 w-4 shrink-0 text-gray-400" />
                          <div>
                            <div>{customer.name}</div>
                            {customer.netsuiteCustomerNumber && (
                              <div className="text-xs text-muted-foreground">{customer.netsuiteCustomerNumber}</div>
                            )}
                          </div>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCustomerLinkDialogOpen(false)}>
              {t('common.cancel')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Year selector + Summary Cards */}
      {summary && (() => {
        // Collect years from transactions and invoices
        const yearSet = new Set<number>()
        if (summary.firstDate) {
          const from = new Date(summary.firstDate).getFullYear()
          const to = summary.lastDate ? new Date(summary.lastDate).getFullYear() : currentYear
          for (let y = from; y <= to; y++) yearSet.add(y)
        }
        for (const inv of (invYearsData?.incomingInvoices?.items || [])) {
          if (inv.invoiceDate) yearSet.add(new Date(inv.invoiceDate).getFullYear())
        }
        if (yearSet.size === 0) yearSet.add(currentYear)
        const years = Array.from(yearSet).sort((a, b) => b - a).map(String)

        return (
        <>
        <div className="mt-6 mb-3 flex items-center gap-2">
          {years.map(y => (
            <button
              key={y}
              onClick={() => setSummaryYear(y)}
              className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
                summaryYear === y
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {y}
            </button>
          ))}
          <button
            onClick={() => setSummaryYear('total')}
            className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${
              summaryYear === 'total'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {t('common.total', 'Total')}
          </button>
        </div>
        {(() => {
          const inYear = (iso?: string) => {
            if (summaryYear === 'total' || !iso) return true
            return iso.startsWith(summaryYear)
          }
          const outFiltered = allOutInvoices.filter((inv: any) => inYear(inv.invoiceDate))
          // Signed: storno negates the original; voided pair → net 0
          const totalOutgoingNet = outFiltered.reduce((sum: number, inv: any) => {
            const amt = parseFloat(inv.totalGross || '0')
            return sum + (inv.documentType === 'storno' ? -amt : amt)
          }, 0)
          const invoiced = parseFloat(summary.totalInvoiced) || 0
          const paidToThem = Math.abs(parseFloat(summary.totalDebit) || 0)
          const receivedFromThem = parseFloat(summary.totalCredit) || 0
          if (accountType === 'debtor') {
            // Debitor: positive = they owe us
            const outstandingFromThem = totalOutgoingNet - receivedFromThem
            return (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
              <div className="rounded-lg border bg-white p-4">
                <p className="text-sm font-medium text-gray-500">{t('banking.invoicedByUs', 'Invoiced (out)')}</p>
                <p className="mt-1 text-xl font-semibold text-gray-900">{formatCurrency(totalOutgoingNet)}</p>
                <p className="mt-1 text-xs text-gray-400">{outFiltered.length} {t('banking.outgoingInvoices', 'outgoing')}</p>
              </div>
              <div className="rounded-lg border bg-white p-4">
                <p className="text-sm font-medium text-gray-500">{t('banking.received', 'Received')}</p>
                <p className="mt-1 text-xl font-semibold text-green-600">{formatCurrency(receivedFromThem)}</p>
                <p className="mt-1 text-xs text-gray-400">{summary.transactionCount} {t('banking.transactions')}</p>
              </div>
              <div className="rounded-lg border bg-white p-4">
                <p className="text-sm font-medium text-gray-500">{t('banking.outstanding', 'Outstanding')}</p>
                <p className={`mt-1 text-xl font-semibold ${outstandingFromThem > 0.01 ? 'text-orange-600' : outstandingFromThem < -0.01 ? 'text-blue-600' : 'text-gray-900'}`}>
                  {formatCurrency(outstandingFromThem)}
                </p>
                <p className="mt-1 text-xs text-gray-400">
                  {outstandingFromThem > 0.01 ? t('banking.theyOwe', 'they owe') : outstandingFromThem < -0.01 ? t('banking.overpaid', 'overpaid') : t('banking.settled', 'settled')}
                </p>
              </div>
              <div className="rounded-lg border bg-white p-4">
                <p className="text-sm font-medium text-gray-500">{t('banking.balance', 'Saldo')}</p>
                <p className={`mt-1 text-xl font-semibold ${outstandingFromThem > 0.01 ? 'text-orange-600' : 'text-gray-900'}`}>
                  {outstandingFromThem < 0 ? `-${formatCurrency(Math.abs(outstandingFromThem))}` : formatCurrency(outstandingFromThem)}
                </p>
                {summary.firstDate && summary.lastDate && (
                  <p className="mt-1 text-xs text-gray-400">{formatDate(summary.firstDate)} – {formatDate(summary.lastDate)}</p>
                )}
              </div>
            </div>
            )
          }
          // Creditor: positive = we owe them
          const outstandingToThem = invoiced - paidToThem
          return (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div className="rounded-lg border bg-white p-4">
              <p className="text-sm font-medium text-gray-500">{t('banking.invoicedByThem', 'Invoiced (in)')}</p>
              <p className="mt-1 text-xl font-semibold text-gray-900">{formatCurrency(summary.totalInvoiced)}</p>
              <p className="mt-1 text-xs text-gray-400">{summary.invoiceCount} {t('incomingInvoices.title', 'invoices')}</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-sm font-medium text-gray-500">{t('banking.paid', 'Paid')}</p>
              <p className="mt-1 text-xl font-semibold text-red-600">{formatCurrency(paidToThem)}</p>
              <p className="mt-1 text-xs text-gray-400">{summary.transactionCount} {t('banking.transactions')}</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-sm font-medium text-gray-500">{t('banking.outstanding', 'Outstanding')}</p>
              <p className={`mt-1 text-xl font-semibold ${outstandingToThem > 0.01 ? 'text-orange-600' : outstandingToThem < -0.01 ? 'text-green-600' : 'text-gray-900'}`}>
                {formatCurrency(outstandingToThem)}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                {outstandingToThem > 0.01 ? t('banking.weOwe', 'we owe') : outstandingToThem < -0.01 ? t('banking.overpaid', 'overpaid') : t('banking.settled', 'settled')}
              </p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-sm font-medium text-gray-500">{t('banking.balance', 'Saldo')}</p>
              <p className={`mt-1 text-xl font-semibold ${outstandingToThem > 0.01 ? 'text-orange-600' : 'text-gray-900'}`}>
                {outstandingToThem < 0 ? `-${formatCurrency(Math.abs(outstandingToThem))}` : formatCurrency(outstandingToThem)}
              </p>
              {summary.firstDate && summary.lastDate && (
                <p className="mt-1 text-xs text-gray-400">{formatDate(summary.firstDate)} – {formatDate(summary.lastDate)}</p>
              )}
            </div>
          </div>
          )
        })()}
        </>
        )
      })()}

      {/* Tabs */}
      <div className="mt-6">
        <div className="flex gap-1 border-b mb-4">
          <button
            onClick={() => setActiveTab('account')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'account'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t('banking.account', 'Account')}
          </button>
          <button
            onClick={() => setActiveTab('transactions')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'transactions'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t('banking.bankTransactions', 'Bank Transactions')}
            {totalCount > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{totalCount}</span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('invoices')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'invoices'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t('incomingInvoices.title', 'Incoming Invoices')}
            {invTotalCount > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{invTotalCount}</span>
            )}
          </button>
          {linkedCustomerId && (
            <button
              onClick={() => setActiveTab('outgoing')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'outgoing'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t('banking.outgoingInvoices', 'Outgoing Invoices')}
              {outTotalCount > 0 && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{outTotalCount}</span>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Account Tab — type-aware ledger */}
      {activeTab === 'account' && (() => {
        // Debitor ledger (customer account): balance > 0 = they owe us
        //   outgoing invoice  → Soll  +gross
        //   outgoing storno   → Haben -gross (credit note reduces their debt)
        //   payment received  → Haben -gross (reduces their debt)
        // Creditor ledger (vendor account): balance > 0 = we owe them
        //   incoming invoice  → Haben +gross
        //   payment sent      → Soll  -gross (reduces our debt)
        interface LedgerEntry {
          date: string
          description: string
          amount: number      // signed for balance calc per account type
          displayAmount: number // absolute amount for Soll/Haben column
          side: 'soll' | 'haben'
          type: 'invoice' | 'outgoing-invoice' | 'outgoing-storno' | 'payment' | 'payment-received'
          id: string
        }

        const entries: LedgerEntry[] = []

        if (accountType === 'debtor') {
          // Outgoing invoices + stornos
          for (const inv of allOutInvoices) {
            const isStorno = inv.documentType === 'storno'
            const gross = parseFloat(inv.totalGross || '0')
            entries.push({
              date: inv.invoiceDate || '',
              description: isStorno
                ? `${t('banking.creditNote', 'Credit Note')}: ${inv.invoiceNumber}${inv.stornoOfNumber ? ` (${t('banking.cancels', 'cancels')} ${inv.stornoOfNumber})` : ''}`
                : `${t('banking.outgoingInvoice', 'Outgoing Invoice')}: ${inv.invoiceNumber}`,
              amount: isStorno ? -gross : +gross,
              displayAmount: gross,
              side: isStorno ? 'haben' : 'soll',
              type: isStorno ? 'outgoing-storno' : 'outgoing-invoice',
              id: `out-${inv.id}`,
            })
          }
          // Payments received (credits)
          for (const tx of transactions) {
            const amt = parseFloat(tx.amount)
            if (amt <= 0) continue
            const matchInfo = tx.matchedInvoice ? ` → ${tx.matchedInvoice.invoiceNumber}` : ''
            entries.push({
              date: tx.entryDate,
              description: `${t('banking.paymentReceived', 'Payment received')}${matchInfo}`,
              amount: -amt,
              displayAmount: amt,
              side: 'haben',
              type: 'payment-received',
              id: `tx-${tx.id}`,
            })
          }
        } else {
          // Creditor: incoming invoices + payments sent
          for (const inv of cpInvoices) {
            entries.push({
              date: inv.invoiceDate || inv.createdAt?.split('T')[0] || '',
              description: `${t('incomingInvoices.invoiceNumber')}: ${inv.invoiceNumber || inv.originalFilename}`,
              amount: +parseFloat(inv.grossAmount || '0'),
              displayAmount: parseFloat(inv.grossAmount || '0'),
              side: 'haben',
              type: 'invoice',
              id: `inv-${inv.id}`,
            })
          }
          for (const tx of transactions) {
            const amt = parseFloat(tx.amount)
            if (amt >= 0) continue
            const matchInfo = tx.matchedInvoice ? ` → ${tx.matchedInvoice.invoiceNumber}` : ''
            entries.push({
              date: tx.entryDate,
              description: `${t('banking.payment', 'Payment')}${matchInfo}`,
              amount: amt, // negative
              displayAmount: Math.abs(amt),
              side: 'soll',
              type: 'payment',
              id: `tx-${tx.id}`,
            })
          }
        }

        // Always sort ascending first to compute running balance correctly
        entries.sort((a, b) => a.date.localeCompare(b.date))

        // Compute running saldo
        let runningBalance = 0
        const ledgerRows = entries.map(e => {
          runningBalance += e.amount
          return { ...e, balance: runningBalance }
        })

        // Apply display sort order
        if (ledgerSortOrder === 'desc') ledgerRows.reverse()

        return (
        <div className="space-y-4">
          {ledgerRows.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <FileText className="mx-auto h-10 w-10 mb-2 opacity-50" />
              <p>{t('banking.noEntries', 'No entries')}</p>
            </div>
          ) : (
            <div className="overflow-x-auto rounded-lg border bg-white">
              <table className="w-full table-fixed text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                    <th className="w-[12%] cursor-pointer whitespace-nowrap px-4 py-3" onClick={() => setLedgerSortOrder(ledgerSortOrder === 'asc' ? 'desc' : 'asc')}>
                      <span className="inline-flex items-center gap-1">
                        {t('incomingInvoices.date')}
                        {ledgerSortOrder === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />}
                      </span>
                    </th>
                    <th className="px-4 py-3">{t('common.description', 'Description')}</th>
                    <th className="w-[12%] px-4 py-3 text-right">{t('banking.soll', 'Soll')}</th>
                    <th className="w-[12%] px-4 py-3 text-right">{t('banking.haben', 'Haben')}</th>
                    <th className="w-[12%] px-4 py-3 text-right">{t('banking.balance', 'Saldo')}</th>
                  </tr>
                </thead>
                <tbody>
                  {ledgerRows.map(row => (
                    <tr key={row.id} className="border-b">
                      <td className="whitespace-nowrap px-4 py-2.5 text-gray-600">{formatDate(row.date)}</td>
                      <td className="px-4 py-2.5 text-gray-900">{row.description}</td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums font-medium text-gray-900">
                        {row.side === 'soll' ? formatCurrency(row.displayAmount) : ''}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums font-medium text-gray-900">
                        {row.side === 'haben' ? formatCurrency(row.displayAmount) : ''}
                      </td>
                      <td className={`whitespace-nowrap px-4 py-2.5 text-right tabular-nums font-medium ${row.balance > 0.01 ? 'text-orange-600' : row.balance < -0.01 ? 'text-green-600' : 'text-gray-900'}`}>
                        {row.balance < 0 ? `-${formatCurrency(Math.abs(row.balance))}` : formatCurrency(row.balance)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        )
      })()}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
      <div className="space-y-4">
        {/* Transaction Table */}
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="w-full table-fixed text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                <th
                  className="w-[100px] cursor-pointer whitespace-nowrap px-4 py-3"
                  onClick={() => handleSort('date')}
                >
                  <span className="inline-flex items-center gap-1">
                    {t('banking.date')}
                    {getSortIcon('date')}
                  </span>
                </th>
                <th
                  className="w-[200px] cursor-pointer px-4 py-3"
                  onClick={() => handleSort('counterparty')}
                >
                  <span className="inline-flex items-center gap-1">
                    {t('banking.counterparty')}
                    {getSortIcon('counterparty')}
                  </span>
                </th>
                <th className="px-4 py-3">{t('banking.bookingText')}</th>
                <th
                  className="w-[120px] cursor-pointer whitespace-nowrap px-4 py-3 text-right"
                  onClick={() => handleSort('amount')}
                >
                  <span className="inline-flex items-center justify-end gap-1">
                    {t('banking.amount')}
                    {getSortIcon('amount')}
                  </span>
                </th>
                <th className="w-[110px] px-4 py-3">{t('banking.account')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {txLoading && transactions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-gray-400">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-12 text-center text-gray-500">
                    {t('banking.noTransactions')}
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => {
                  const amount = parseFloat(tx.amount)
                  const isExpanded = expandedTxId === tx.id
                  return (
                    <tr
                      key={tx.id}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => setExpandedTxId(isExpanded ? null : tx.id)}
                    >
                      <td className="whitespace-nowrap px-4 py-2.5 text-gray-900">
                        {formatDate(tx.entryDate)}
                      </td>
                      <td className="max-w-[220px] px-4 py-2.5 text-gray-900">
                        <div className="truncate">
                          {tx.counterparty?.name ? (
                            <Link
                              to={`/banking/counterparty/${tx.counterparty.id}`}
                              onClick={(e) => e.stopPropagation()}
                              className="truncate text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              {tx.counterparty.name}
                            </Link>
                          ) : (
                            <span>-</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-gray-600">
                        {isExpanded ? (
                          <div className="space-y-2">
                            <div className="whitespace-pre-wrap">{tx.bookingText || '-'}</div>
                            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                              {tx.valueDate && (
                                <>
                                  <span className="text-gray-400">{t('banking.valueDate')}</span>
                                  <span className="text-gray-600">{formatDate(tx.valueDate)}</span>
                                </>
                              )}
                              {tx.reference && (
                                <>
                                  <span className="text-gray-400">{t('banking.reference')}</span>
                                  <span className="break-all text-gray-600">{tx.reference}</span>
                                </>
                              )}
                              {tx.counterparty?.iban && (
                                <>
                                  <span className="text-gray-400">{t('banking.iban')}</span>
                                  <span className="text-gray-600">{tx.counterparty.iban}</span>
                                </>
                              )}
                              {tx.counterparty?.bic && (
                                <>
                                  <span className="text-gray-400">{t('banking.bic')}</span>
                                  <span className="text-gray-600">{tx.counterparty.bic}</span>
                                </>
                              )}
                              {tx.transactionType && (
                                <>
                                  <span className="text-gray-400">{t('banking.transactionType')}</span>
                                  <span className="text-gray-600">{tx.transactionType}</span>
                                </>
                              )}
                            </div>
                          </div>
                        ) : (
                          <span className="block truncate">{tx.bookingText || '-'}</span>
                        )}
                      </td>
                      <td className={`whitespace-nowrap px-4 py-2.5 text-right font-medium ${amount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setMatchSheetTxId(tx.id)
                              setMatchSheetOpen(true)
                            }}
                            className={`${tx.matchedInvoice ? 'text-blue-600 hover:text-blue-800' : 'text-gray-300 hover:text-gray-500'}`}
                            title={t('banking.matchView.matchButton')}
                          >
                            <Link2 className="h-4 w-4" />
                          </button>
                          {tx.matchedInvoice && (
                            <Link
                              to={
                                tx.matchedInvoice.invoiceType === 'incoming'
                                  ? `/incoming-invoices?id=${tx.matchedInvoice.invoiceId}`
                                  : tx.matchedInvoice.invoiceType === 'imported'
                                  ? `/invoices/${tx.matchedInvoice.invoiceId}?type=imported`
                                  : `/invoices/${tx.matchedInvoice.invoiceId}`
                              }
                              onClick={(e) => e.stopPropagation()}
                              className="text-blue-600 hover:text-blue-800"
                              title={`${t('banking.matchedInvoice')}: ${tx.matchedInvoice.invoiceNumber}`}
                            >
                              <FileText className="h-4 w-4" />
                            </Link>
                          )}
                          {formatCurrency(tx.amount, { currency: tx.currency || 'EUR' })}
                        </div>
                      </td>
                      <td className="whitespace-nowrap px-4 py-2.5 text-gray-500">
                        {tx.accountName}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination — hide if less than 10 entries */}
        {totalCount > 10 && (
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              {t('common.pagination.showing', {
                from: (page - 1) * pageSize + 1,
                to: Math.min(page * pageSize, totalCount),
                total: totalCount,
              })}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                <ChevronLeft className="h-4 w-4" />
                {t('common.pagination.previous')}
              </button>
              <span className="text-sm text-gray-500">
                {t('common.pagination.page', { page, totalPages: totalPages || 1 })}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={!hasNextPage}
                className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                {t('common.pagination.next')}
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
      )}

      {/* Invoices Tab */}
      {activeTab === 'invoices' && (() => {
        const handleInvSort = (field: string) => {
          if (invSortBy === field) {
            setInvSortOrder(invSortOrder === 'asc' ? 'desc' : 'asc')
          } else {
            setInvSortBy(field)
            setInvSortOrder('desc')
          }
        }
        const getInvSortIcon = (field: string) => {
          if (invSortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />
          return invSortOrder === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />
        }

        return (
        <div className="space-y-4">
          {invLoading ? (
            <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : cpInvoices.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Receipt className="mx-auto h-10 w-10 mb-2 opacity-50" />
              <p>{t('incomingInvoices.empty')}</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border bg-white">
                <table className="w-full table-fixed text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      <th className="w-[12%] cursor-pointer whitespace-nowrap px-4 py-3" onClick={() => handleInvSort('invoice_date')}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.date')}{getInvSortIcon('invoice_date')}</span>
                      </th>
                      <th className="cursor-pointer px-4 py-3" onClick={() => handleInvSort('supplier_name')}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.supplier')}{getInvSortIcon('supplier_name')}</span>
                      </th>
                      <th className="w-[18%] cursor-pointer px-4 py-3" onClick={() => handleInvSort('invoice_number')}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.invoiceNumber')}{getInvSortIcon('invoice_number')}</span>
                      </th>
                      <th className="w-[12%] cursor-pointer whitespace-nowrap px-4 py-3 text-right" onClick={() => handleInvSort('gross_amount')}>
                        <span className="inline-flex items-center justify-end gap-1">{t('incomingInvoices.grossAmount')}{getInvSortIcon('gross_amount')}</span>
                      </th>
                      <th className="w-[12%] cursor-pointer px-4 py-3" onClick={() => handleInvSort('extraction_status')}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.statusLabel')}{getInvSortIcon('extraction_status')}</span>
                      </th>
                      <th className="w-[10%] px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {cpInvoices.map((inv: any) => (
                      <tr key={inv.id} className="border-b">
                        <td className="whitespace-nowrap px-4 py-2.5 text-gray-600">{formatDate(inv.invoiceDate)}</td>
                        <td className="px-4 py-2.5 font-medium text-gray-900 truncate">{inv.supplierName || inv.originalFilename}</td>
                        <td className="px-4 py-2.5 text-gray-600">{inv.invoiceNumber || '—'}</td>
                        <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums">
                          {formatCurrency(inv.grossAmount, { currency: inv.currency })}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant="secondary" className={invoiceStatusColors[inv.extractionStatus] || ''}>
                            {t(`incomingInvoices.status.${inv.extractionStatus === 'extraction_failed' ? 'extractionFailed' : inv.extractionStatus}`)}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-1">
                            {inv.pdfUrl && (
                              <a
                                href={inv.pdfUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                                title={t('common.viewPdf', 'View PDF')}
                              >
                                <Eye className="h-4 w-4" />
                              </a>
                            )}
                            <button
                              onClick={() => setSelectedInvId(inv.id)}
                              className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                              title={t('common.details', 'Details')}
                            >
                              <SearchIcon className="h-4 w-4" />
                            </button>
                            {(() => {
                              // Find debit transactions that could match this invoice
                              const invAmount = Math.abs(parseFloat(inv.grossAmount || '0'))
                              // Prefer exact amount match, otherwise first unmatched debit
                              const exactTx = transactions.find(
                                (tx: any) => parseFloat(tx.amount) < 0 && Math.abs(Math.abs(parseFloat(tx.amount)) - invAmount) < 0.01 && !tx.matchedInvoice
                              )
                              const anyDebitTx = exactTx || transactions.find(
                                (tx: any) => parseFloat(tx.amount) < 0 && !tx.matchedInvoice
                              )
                              const matchTxId = anyDebitTx?.id || (transactions.find((tx: any) => parseFloat(tx.amount) < 0)?.id)
                              return matchTxId ? (
                                <button
                                  onClick={() => {
                                    setMatchSheetTxId(matchTxId)
                                    setMatchSheetOpen(true)
                                  }}
                                  className={`rounded p-1 hover:bg-gray-100 ${exactTx ? 'text-blue-500 hover:text-blue-700' : 'text-gray-400 hover:text-gray-600'}`}
                                  title={exactTx
                                    ? `${t('banking.matchView.matchButton', 'Match')} — ${formatDate(exactTx.entryDate)} ${formatCurrency(exactTx.amount)}`
                                    : t('banking.matchView.matchButton', 'Match')
                                  }
                                >
                                  <ChainIcon className="h-4 w-4" />
                                </button>
                              ) : null
                            })()}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {invTotalCount > 10 && (
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>{invPage * 50 - 49}–{Math.min(invPage * 50, invTotalCount)} of {invTotalCount}</span>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setInvPage(invPage - 1)} disabled={invPage <= 1} className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                      <ChevronLeft className="h-4 w-4" />{t('common.pagination.previous')}
                    </button>
                    <button onClick={() => setInvPage(invPage + 1)} disabled={!invHasNextPage} className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                      {t('common.pagination.next')}<ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
        )
      })()}

      {/* Outgoing Invoices Tab */}
      {activeTab === 'outgoing' && (
        <div className="space-y-4">
          {outLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
          ) : outInvoices.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Receipt className="mx-auto h-10 w-10 mb-2 opacity-50" />
              <p>{t('banking.noOutgoingInvoices', 'No outgoing invoices')}</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border bg-white">
                <table className="w-full table-fixed text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      <th className="w-[12%] cursor-pointer px-4 py-3" onClick={() => { setOutSortBy('invoiceDate'); setOutSortOrder(outSortBy === 'invoiceDate' && outSortOrder === 'desc' ? 'asc' : 'desc') }}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.date')}{outSortBy === 'invoiceDate' ? (outSortOrder === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />) : <ArrowUpDown className="h-3.5 w-3.5" />}</span>
                      </th>
                      <th className="w-[18%] cursor-pointer px-4 py-3" onClick={() => { setOutSortBy('invoiceNumber'); setOutSortOrder(outSortBy === 'invoiceNumber' && outSortOrder === 'desc' ? 'asc' : 'desc') }}>
                        <span className="inline-flex items-center gap-1">{t('incomingInvoices.invoiceNumber')}{outSortBy === 'invoiceNumber' ? (outSortOrder === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />) : <ArrowUpDown className="h-3.5 w-3.5" />}</span>
                      </th>
                      <th className="px-4 py-3">{t('contracts.title', 'Contract')}</th>
                      <th className="w-[14%] cursor-pointer px-4 py-3 text-right" onClick={() => { setOutSortBy('totalGross'); setOutSortOrder(outSortBy === 'totalGross' && outSortOrder === 'desc' ? 'asc' : 'desc') }}>
                        <span className="inline-flex items-center justify-end gap-1">{t('incomingInvoices.grossAmount')}{outSortBy === 'totalGross' ? (outSortOrder === 'asc' ? <ArrowUp className="h-3.5 w-3.5" /> : <ArrowDown className="h-3.5 w-3.5" />) : <ArrowUpDown className="h-3.5 w-3.5" />}</span>
                      </th>
                      <th className="w-[10%] px-4 py-3">{t('incomingInvoices.statusLabel')}</th>
                      <th className="w-[8%] px-4 py-3 text-right">{t('common.actions', 'Actions')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {outInvoices.map((inv: any) => {
                      const isStorno = inv.documentType === 'storno'
                      const gross = parseFloat(inv.totalGross || '0')
                      return (
                      <tr key={inv.id} className="border-b hover:bg-gray-50">
                        <td className="whitespace-nowrap px-4 py-2.5 text-gray-600">{formatDate(inv.invoiceDate)}</td>
                        <td className="px-4 py-2.5">
                          <div className="flex items-center gap-1.5">
                            <Link to={`/invoices/${inv.id}`} className="text-blue-600 hover:underline">{inv.invoiceNumber}</Link>
                            {isStorno && (
                              <Badge variant="secondary" className="bg-purple-100 text-purple-800 text-[10px] px-1.5 py-0">
                                {t('banking.creditNote', 'Gutschrift')}
                              </Badge>
                            )}
                          </div>
                          {isStorno && inv.stornoOfNumber && (
                            <div className="text-xs text-gray-400 mt-0.5">{t('banking.cancels', 'storniert')} {inv.stornoOfNumber}</div>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-gray-600 truncate" title={inv.contractName}>{inv.contractName || '—'}</td>
                        <td className={`whitespace-nowrap px-4 py-2.5 text-right tabular-nums ${isStorno ? 'text-purple-700' : ''}`}>
                          {isStorno ? `-${formatCurrency(gross)}` : formatCurrency(gross)}
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant="secondary" className={inv.isPaid ? 'bg-green-100 text-green-800' : inv.status === 'voided' ? 'bg-gray-100 text-gray-500 line-through' : 'bg-gray-100 text-gray-700'}>
                            {inv.isPaid ? t('banking.paid', 'Paid') : inv.status}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-right">
                          {inv.pdfUrl && (
                            <a href={inv.pdfUrl} target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-gray-500 hover:text-gray-700" title="PDF">
                              <FileText className="h-4 w-4" />
                            </a>
                          )}
                        </td>
                      </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              {outTotalCount > 50 && (
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>{outPage * 50 - 49}–{Math.min(outPage * 50, outTotalCount)} of {outTotalCount}</span>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setOutPage(outPage - 1)} disabled={outPage <= 1} className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                      <ChevronLeft className="h-4 w-4" />{t('common.pagination.previous')}
                    </button>
                    <button onClick={() => setOutPage(outPage + 1)} disabled={!outHasNextPage} className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                      {t('common.pagination.next')}<ChevronRight className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Transaction Match Sheet */}
      <TransactionMatchSheet
        transactionId={matchSheetTxId}
        open={matchSheetOpen}
        onOpenChange={(open) => {
          setMatchSheetOpen(open)
          if (!open) setMatchSheetTxId(null)
        }}
        onMatchChanged={() => txRefetch()}
      />

      {selectedInvId && (
        <IncomingInvoiceDetail
          id={selectedInvId}
          open={!!selectedInvId}
          onClose={() => setSelectedInvId(null)}
          onUpdate={() => {}}
        />
      )}
    </div>
  )
}
