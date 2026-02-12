import { useState, useRef, useCallback, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  Landmark,
  Plus,
  Upload,
  Loader2,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
  FileText,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import { useAuth } from '@/lib/auth'

// --- GraphQL ---

const BANK_ACCOUNTS = gql`
  query BankAccounts {
    bankAccounts {
      id
      name
      bankCode
      accountNumber
      iban
      bic
      transactionCount
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
    $unmatchedCreditsOnly: Boolean
    $sortBy: String
    $sortOrder: String
    $page: Int
    $pageSize: Int
    $centerOnId: Int
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
      unmatchedCreditsOnly: $unmatchedCreditsOnly
      sortBy: $sortBy
      sortOrder: $sortOrder
      page: $page
      pageSize: $pageSize
      centerOnId: $centerOnId
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
          contractId
          customerId
        }
      }
      totalCount
      page
      pageSize
      hasNextPage
    }
  }
`

const CREATE_BANK_ACCOUNT = gql`
  mutation CreateBankAccount($input: CreateBankAccountInput!) {
    createBankAccount(input: $input) {
      success
      error
      account {
        id
        name
        bankCode
        accountNumber
        iban
        bic
        transactionCount
      }
    }
  }
`

const UPDATE_BANK_ACCOUNT = gql`
  mutation UpdateBankAccount($input: UpdateBankAccountInput!) {
    updateBankAccount(input: $input) {
      success
      error
      account {
        id
        name
        bankCode
        accountNumber
        iban
        bic
        transactionCount
      }
    }
  }
`

const DELETE_BANK_ACCOUNT = gql`
  mutation DeleteBankAccount($id: Int!) {
    deleteBankAccount(id: $id) {
      success
      error
    }
  }
`

const CREATE_COUNTERPARTY = gql`
  mutation CreateCounterparty($input: CreateCounterpartyInput!) {
    createCounterparty(input: $input) {
      success
      error
      counterparty {
        id
        name
        iban
        bic
      }
    }
  }
`

const UPDATE_TRANSACTION_COUNTERPARTY = gql`
  mutation UpdateTransactionCounterparty($input: UpdateTransactionCounterpartyInput!) {
    updateTransactionCounterparty(input: $input) {
      success
      error
    }
  }
`

const SEARCH_COUNTERPARTIES = gql`
  query SearchCounterparties($search: String, $pageSize: Int) {
    counterparties(search: $search, pageSize: $pageSize) {
      items {
        id
        name
        iban
      }
    }
  }
`

const BANK_COUNTERPARTIES = gql`
  query BankCounterparties(
    $search: String
    $sortBy: String
    $sortOrder: String
    $page: Int
    $pageSize: Int
  ) {
    counterparties(
      search: $search
      sortBy: $sortBy
      sortOrder: $sortOrder
      page: $page
      pageSize: $pageSize
    ) {
      items {
        id
        name
        totalDebit
        totalCredit
        transactionCount
        firstDate
        lastDate
      }
      totalCount
      page
      pageSize
      hasNextPage
    }
  }
`

// --- Types ---

interface BankAccount {
  id: number
  name: string
  bankCode: string
  accountNumber: string
  iban: string
  bic: string
  transactionCount: number
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
  matchedInvoice: { invoiceId: string; invoiceNumber: string; contractId: number | null; customerId: number | null } | null
}

// --- Component ---

export function BankingPage() {
  const { t } = useTranslation()
  const { token } = useAuth()
  const navigate = useNavigate()
  const [, setSearchParams] = useSearchParams()

  // Tab state
  const [activeTab, setActiveTab] = useState<'transactions' | 'counterparties'>('transactions')

  // Counterparty list state
  const [cpSearch, setCpSearch] = useState('')
  const [cpDebouncedSearch, setCpDebouncedSearch] = useState('')
  const [cpSortBy, setCpSortBy] = useState<string>('totalAmount')
  const [cpSortOrder, setCpSortOrder] = useState<string>('desc')
  const [cpPage, setCpPage] = useState(1)
  const cpPageSize = 50

  // Expanded transaction row
  const [expandedTxId, setExpandedTxId] = useState<number | null>(null)

  // Edit counterparty state
  const [editingTxCounterparty, setEditingTxCounterparty] = useState<BankTransaction | null>(null)
  const [cpSearchQuery, setCpSearchQuery] = useState('')
  const [cpSearchDebounced, setCpSearchDebounced] = useState('')
  const [newCpName, setNewCpName] = useState('')
  const [showCreateCp, setShowCreateCp] = useState(false)

  // Account dialog state
  const [accountDialogOpen, setAccountDialogOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<BankAccount | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null)
  const [accountForm, setAccountForm] = useState({
    name: '',
    bankCode: '',
    accountNumber: '',
    iban: '',
    bic: '',
  })
  const [accountError, setAccountError] = useState<string | null>(null)

  // Upload state
  const [uploadingAccountId, setUploadingAccountId] = useState<number | null>(null)
  const [uploadResult, setUploadResult] = useState<{ imported: number; skipped: number } | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Transaction filters
  const [filterAccountId, setFilterAccountId] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [amountMin, setAmountMin] = useState('')
  const [amountMax, setAmountMax] = useState('')
  const [direction, setDirection] = useState<string>('all')
  const [unmatchedCredits, setUnmatchedCredits] = useState(false)
  const [sortBy, setSortBy] = useState('date')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const pageSize = 50

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  // Debounce counterparty search
  useEffect(() => {
    const timer = setTimeout(() => setCpDebouncedSearch(cpSearch), 300)
    return () => clearTimeout(timer)
  }, [cpSearch])

  // Reset page on filter change
  useEffect(() => {
    setPage(1)
  }, [filterAccountId, debouncedSearch, dateFrom, dateTo, amountMin, amountMax, direction, unmatchedCredits])

  // Reset counterparty page on filter change
  useEffect(() => {
    setCpPage(1)
  }, [cpDebouncedSearch])

  // Track target transaction from URL
  const [targetTxId, setTargetTxId] = useState<number | null>(() => {
    const txParam = new URLSearchParams(window.location.search).get('tx')
    return txParam ? parseInt(txParam, 10) : null
  })

  // Clear filters when we have a target transaction to maximize chance of finding it
  useEffect(() => {
    if (targetTxId) {
      // Reset all filters so centerOnId can find the transaction
      setFilterAccountId('all')
      setSearchQuery('')
      setDebouncedSearch('')
      setDateFrom('')
      setDateTo('')
      setAmountMin('')
      setAmountMax('')
      setDirection('all')
      setUnmatchedCredits(false)
    }
  }, []) // Only run once on mount

  // Queries
  const { data: accountsData, loading: accountsLoading, refetch: refetchAccounts } = useQuery(BANK_ACCOUNTS)
  const accounts: BankAccount[] = accountsData?.bankAccounts ?? []

  const { data: txData, loading: txLoading } = useQuery(BANK_TRANSACTIONS, {
    variables: {
      accountId: filterAccountId !== 'all' ? parseInt(filterAccountId) : null,
      search: debouncedSearch || null,
      dateFrom: dateFrom || null,
      dateTo: dateTo || null,
      amountMin: amountMin ? parseFloat(amountMin) : null,
      amountMax: amountMax ? parseFloat(amountMax) : null,
      direction: direction !== 'all' ? direction : null,
      unmatchedCreditsOnly: unmatchedCredits,
      sortBy,
      sortOrder,
      page,
      pageSize,
      centerOnId: targetTxId,
    },
    fetchPolicy: 'cache-and-network',
  })

  const transactions: BankTransaction[] = txData?.bankTransactions?.items ?? []
  const totalCount = txData?.bankTransactions?.totalCount ?? 0
  const hasNextPage = txData?.bankTransactions?.hasNextPage ?? false
  const returnedPage = txData?.bankTransactions?.page ?? page
  const totalPages = Math.ceil(totalCount / pageSize)

  // Handle URL parameter for transaction expansion - wait for data to load
  useEffect(() => {
    if (targetTxId && !txLoading && transactions.length > 0) {
      const txExists = transactions.some(tx => tx.id === targetTxId)
      if (txExists) {
        setExpandedTxId(targetTxId)
        // Sync page state with what backend returned (may be different due to centerOnId)
        if (returnedPage !== page) {
          setPage(returnedPage)
        }
        // Clear the param from URL after successfully finding transaction
        setSearchParams((prev) => {
          prev.delete('tx')
          return prev
        }, { replace: true })
        setTargetTxId(null)
        // Scroll to the transaction row after a brief delay
        setTimeout(() => {
          const row = document.querySelector(`[data-tx-id="${targetTxId}"]`)
          if (row) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' })
          }
        }, 100)
      }
    }
  }, [targetTxId, txLoading, transactions, returnedPage, page, setSearchParams])

  // Counterparties query
  const { data: cpData, loading: cpLoading } = useQuery(BANK_COUNTERPARTIES, {
    variables: {
      search: cpDebouncedSearch || null,
      sortBy: cpSortBy,
      sortOrder: cpSortOrder,
      page: cpPage,
      pageSize: cpPageSize,
    },
    skip: activeTab !== 'counterparties',
    fetchPolicy: 'cache-and-network',
  })
  const counterparties = cpData?.counterparties?.items ?? []
  const cpTotalCount = cpData?.counterparties?.totalCount ?? 0
  const cpHasNextPage = cpData?.counterparties?.hasNextPage ?? false
  const cpTotalPages = Math.ceil(cpTotalCount / cpPageSize)

  // Mutations
  const [createAccount, { loading: creating }] = useMutation(CREATE_BANK_ACCOUNT)
  const [updateAccount, { loading: updating }] = useMutation(UPDATE_BANK_ACCOUNT)
  const [deleteAccount, { loading: deleting }] = useMutation(DELETE_BANK_ACCOUNT)
  const [createCounterparty, { loading: creatingCp }] = useMutation(CREATE_COUNTERPARTY)
  const [updateTxCounterparty, { loading: updatingTxCp }] = useMutation(UPDATE_TRANSACTION_COUNTERPARTY)

  // Search counterparties for popover
  const { data: cpSearchData } = useQuery(SEARCH_COUNTERPARTIES, {
    variables: { search: cpSearchDebounced || null, pageSize: 20 },
    skip: !editingTxCounterparty,
  })
  const searchedCounterparties: Counterparty[] = cpSearchData?.counterparties?.items ?? []

  // Debounce counterparty search in popover
  useEffect(() => {
    const timer = setTimeout(() => setCpSearchDebounced(cpSearchQuery), 200)
    return () => clearTimeout(timer)
  }, [cpSearchQuery])

  // Handlers

  const openCreateDialog = () => {
    setEditingAccount(null)
    setAccountForm({ name: '', bankCode: '', accountNumber: '', iban: '', bic: '' })
    setAccountError(null)
    setAccountDialogOpen(true)
  }

  const openEditDialog = (account: BankAccount) => {
    setEditingAccount(account)
    setAccountForm({
      name: account.name,
      bankCode: account.bankCode,
      accountNumber: account.accountNumber,
      iban: account.iban,
      bic: account.bic,
    })
    setAccountError(null)
    setAccountDialogOpen(true)
  }

  const handleSaveAccount = async () => {
    setAccountError(null)
    if (!accountForm.name.trim() || !accountForm.bankCode.trim() || !accountForm.accountNumber.trim()) {
      setAccountError('Name, bank code and account number are required.')
      return
    }

    try {
      if (editingAccount) {
        const { data } = await updateAccount({
          variables: {
            input: {
              id: editingAccount.id,
              name: accountForm.name.trim(),
              iban: accountForm.iban.trim(),
              bic: accountForm.bic.trim(),
            },
          },
        })
        if (!data?.updateBankAccount?.success) {
          setAccountError(data?.updateBankAccount?.error || 'Failed to update account.')
          return
        }
      } else {
        const { data } = await createAccount({
          variables: {
            input: {
              name: accountForm.name.trim(),
              bankCode: accountForm.bankCode.trim(),
              accountNumber: accountForm.accountNumber.trim(),
              iban: accountForm.iban.trim(),
              bic: accountForm.bic.trim(),
            },
          },
        })
        if (!data?.createBankAccount?.success) {
          setAccountError(data?.createBankAccount?.error || 'Failed to create account.')
          return
        }
      }
      setAccountDialogOpen(false)
      refetchAccounts()
    } catch {
      setAccountError('An unexpected error occurred.')
    }
  }

  const handleDeleteAccount = async () => {
    if (!deleteConfirmId) return
    try {
      const { data } = await deleteAccount({ variables: { id: deleteConfirmId } })
      if (data?.deleteBankAccount?.success) {
        setDeleteConfirmId(null)
        refetchAccounts()
      }
    } catch {
      // ignore
    }
  }

  const handleSelectCounterparty = async (counterpartyId: string) => {
    if (!editingTxCounterparty) return
    try {
      const { data } = await updateTxCounterparty({
        variables: {
          input: {
            transactionId: editingTxCounterparty.id,
            counterpartyId,
          },
        },
        refetchQueries: [{ query: BANK_TRANSACTIONS, variables: {
          accountId: filterAccountId !== 'all' ? parseInt(filterAccountId) : null,
          search: debouncedSearch || null,
          dateFrom: dateFrom || null,
          dateTo: dateTo || null,
          amountMin: amountMin ? parseFloat(amountMin) : null,
          amountMax: amountMax ? parseFloat(amountMax) : null,
          direction: direction !== 'all' ? direction : null,
          sortBy,
          sortOrder,
          page,
          pageSize,
        }}],
      })
      if (data?.updateTransactionCounterparty?.success) {
        setEditingTxCounterparty(null)
        setCpSearchQuery('')
      }
    } catch {
      // ignore
    }
  }

  const handleCreateAndSelectCounterparty = async () => {
    if (!editingTxCounterparty || !newCpName.trim()) return
    try {
      const { data } = await createCounterparty({
        variables: {
          input: { name: newCpName.trim() },
        },
      })
      if (data?.createCounterparty?.success && data.createCounterparty.counterparty) {
        await handleSelectCounterparty(data.createCounterparty.counterparty.id)
        setNewCpName('')
        setShowCreateCp(false)
      }
    } catch {
      // ignore
    }
  }

  const handleUploadClick = (accountId: number) => {
    setUploadingAccountId(accountId)
    setUploadResult(null)
    setUploadError(null)
    fileInputRef.current?.click()
  }

  const handleFileChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !uploadingAccountId) return

    setUploadError(null)
    setUploadResult(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const resp = await fetch(`/api/banking/upload/${uploadingAccountId}/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const result = await resp.json()
      if (resp.ok) {
        setUploadResult({ imported: result.imported, skipped: result.skipped })
        refetchAccounts()
      } else {
        setUploadError(result.error || t('banking.uploadError'))
      }
    } catch {
      setUploadError(t('banking.uploadError'))
    } finally {
      setUploadingAccountId(null)
      e.target.value = ''
    }
  }, [uploadingAccountId, token, t, refetchAccounts])

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

  const formatAmount = (amount: string, currency: string) => {
    const num = parseFloat(amount)
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: currency || 'EUR',
    }).format(num)
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('de-DE')
  }

  const clearFilters = () => {
    setFilterAccountId('all')
    setSearchQuery('')
    setDateFrom('')
    setDateTo('')
    setAmountMin('')
    setAmountMax('')
    setDirection('all')
    setUnmatchedCredits(false)
    setPage(1)
  }

  const handleCpSort = (field: string) => {
    if (cpSortBy === field) {
      setCpSortOrder(cpSortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setCpSortBy(field)
      setCpSortOrder('desc')
    }
  }

  const getCpSortIcon = (field: string) => {
    if (cpSortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />
    return cpSortOrder === 'asc'
      ? <ArrowUp className="h-3.5 w-3.5" />
      : <ArrowDown className="h-3.5 w-3.5" />
  }

  const hasActiveFilters = filterAccountId !== 'all' || searchQuery || dateFrom || dateTo || amountMin || amountMax || direction !== 'all' || unmatchedCredits

  // --- Render ---

  if (accountsLoading && !accountsData) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('banking.title')}</h1>
        <button
          onClick={openCreateDialog}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          {t('banking.addAccount')}
        </button>
      </div>

      {/* Accounts Section */}
      {accounts.length === 0 ? (
        <div className="mt-4 rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
          <Landmark className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">{t('banking.noAccounts')}</h3>
          <p className="mt-2 text-sm text-gray-500">{t('banking.createFirst')}</p>
          <button
            onClick={openCreateDialog}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('banking.addAccount')}
          </button>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account) => (
            <div
              key={account.id}
              className="rounded-lg border bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-semibold text-gray-900">
                    {account.name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">
                    {account.bankCode} / {account.accountNumber}
                  </p>
                  {account.iban && (
                    <p className="mt-0.5 text-xs text-gray-400">{account.iban}</p>
                  )}
                </div>
                <div className="ml-2 flex gap-1">
                  <button
                    onClick={() => openEditDialog(account)}
                    className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                    title={t('banking.editAccount')}
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(account.id)}
                    className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                    title={t('banking.deleteAccount')}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  {t('banking.transactionCount', { count: account.transactionCount })}
                </span>
                <button
                  onClick={() => handleUploadClick(account.id)}
                  disabled={uploadingAccountId === account.id}
                  className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  {uploadingAccountId === account.id ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Upload className="h-3.5 w-3.5" />
                  )}
                  {t('banking.uploadStatement')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload feedback */}
      {uploadResult && (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
          {t('banking.uploadSuccess', { imported: uploadResult.imported, skipped: uploadResult.skipped })}
          <button onClick={() => setUploadResult(null)} className="ml-2 text-green-600 hover:text-green-800">
            <X className="inline h-4 w-4" />
          </button>
        </div>
      )}
      {uploadError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {uploadError}
          <button onClick={() => setUploadError(null)} className="ml-2 text-red-600 hover:text-red-800">
            <X className="inline h-4 w-4" />
          </button>
        </div>
      )}

      {/* Hidden file input for MT940 upload */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".sta,.mt940,.txt,.940"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Tabs + Content */}
      {accounts.length > 0 && (
        <div className="mt-6 space-y-4">
          {/* Tab switcher */}
          <div className="flex items-center gap-4 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('transactions')}
              className={`border-b-2 px-1 pb-2 text-sm font-medium ${
                activeTab === 'transactions'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {t('banking.transactions')}
            </button>
            <button
              onClick={() => setActiveTab('counterparties')}
              className={`border-b-2 px-1 pb-2 text-sm font-medium ${
                activeTab === 'counterparties'
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {t('banking.counterparties')}
            </button>
          </div>

          {/* Counterparties Tab */}
          {activeTab === 'counterparties' && (
            <div className="space-y-4">
              {/* Search */}
              <div className="max-w-sm">
                <input
                  type="text"
                  value={cpSearch}
                  onChange={(e) => setCpSearch(e.target.value)}
                  placeholder={t('common.search')}
                  className="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              {/* Table */}
              <div className="overflow-x-auto rounded-lg border bg-white">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                      <th
                        className="cursor-pointer px-4 py-3"
                        onClick={() => handleCpSort('name')}
                      >
                        <span className="inline-flex items-center gap-1">
                          {t('banking.counterparty')}
                          {getCpSortIcon('name')}
                        </span>
                      </th>
                      <th
                        className="cursor-pointer whitespace-nowrap px-4 py-3 text-right"
                        onClick={() => handleCpSort('transactionCount')}
                      >
                        <span className="inline-flex items-center justify-end gap-1">
                          {t('banking.transactions')}
                          {getCpSortIcon('transactionCount')}
                        </span>
                      </th>
                      <th
                        className="cursor-pointer whitespace-nowrap px-4 py-3 text-right"
                        onClick={() => handleCpSort('totalAmount')}
                      >
                        <span className="inline-flex items-center justify-end gap-1">
                          {t('banking.totalAmount')}
                          {getCpSortIcon('totalAmount')}
                        </span>
                      </th>
                      <th
                        className="cursor-pointer whitespace-nowrap px-4 py-3"
                        onClick={() => handleCpSort('lastDate')}
                      >
                        <span className="inline-flex items-center gap-1">
                          {t('banking.lastTransaction')}
                          {getCpSortIcon('lastDate')}
                        </span>
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {cpLoading && counterparties.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-12 text-center text-gray-400">
                          <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                        </td>
                      </tr>
                    ) : counterparties.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-4 py-12 text-center text-gray-500">
                          {t('banking.noCounterparties')}
                        </td>
                      </tr>
                    ) : (
                      counterparties.map((cp: { id: string; name: string; transactionCount: number; totalDebit: string; totalCredit: string; lastDate: string }) => {
                        const totalDebit = parseFloat(cp.totalDebit)
                        const totalCredit = parseFloat(cp.totalCredit)
                        const netAmount = totalDebit + totalCredit
                        return (
                          <tr
                            key={cp.id}
                            className="cursor-pointer hover:bg-gray-50"
                            onClick={() => navigate(`/banking/counterparty/${cp.id}`)}
                          >
                            <td className="px-4 py-2.5 font-medium text-gray-900">
                              {cp.name}
                            </td>
                            <td className="whitespace-nowrap px-4 py-2.5 text-right text-gray-600">
                              {cp.transactionCount}
                            </td>
                            <td className={`whitespace-nowrap px-4 py-2.5 text-right font-medium ${netAmount < 0 ? 'text-red-600' : 'text-green-600'}`}>
                              {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(netAmount)}
                            </td>
                            <td className="whitespace-nowrap px-4 py-2.5 text-gray-600">
                              {formatDate(cp.lastDate)}
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              {cpTotalCount > 0 && (
                <div className="flex items-center justify-between text-sm text-gray-600">
                  <span>
                    {t('common.pagination.showing', {
                      from: (cpPage - 1) * cpPageSize + 1,
                      to: Math.min(cpPage * cpPageSize, cpTotalCount),
                      total: cpTotalCount,
                    })}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setCpPage(cpPage - 1)}
                      disabled={cpPage <= 1}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      {t('common.pagination.previous')}
                    </button>
                    <span className="text-sm text-gray-500">
                      {t('common.pagination.page', { page: cpPage, totalPages: cpTotalPages || 1 })}
                    </span>
                    <button
                      onClick={() => setCpPage(cpPage + 1)}
                      disabled={!cpHasNextPage}
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

          {/* Transactions Tab */}
          {activeTab === 'transactions' && (
          <>
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">{t('banking.transactions')}</h2>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                {t('banking.filters')} <X className="inline h-3 w-3" />
              </button>
            )}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-gray-50 p-3">
            {/* Search */}
            <div className="min-w-[200px] flex-1">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('common.search')}
              </label>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('common.search')}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Account filter */}
            <div className="w-[180px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.account')}
              </label>
              <Select value={filterAccountId} onValueChange={setFilterAccountId}>
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('banking.allAccounts')}</SelectItem>
                  {accounts.map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Date range */}
            <div className="w-[130px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.dateFrom')}
              </label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="w-[130px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.dateTo')}
              </label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Amount range */}
            <div className="w-[100px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.amountMin')}
              </label>
              <input
                type="number"
                step="0.01"
                value={amountMin}
                onChange={(e) => setAmountMin(e.target.value)}
                className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="w-[100px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.amountMax')}
              </label>
              <input
                type="number"
                step="0.01"
                value={amountMax}
                onChange={(e) => setAmountMax(e.target.value)}
                className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Direction */}
            <div className="w-[130px]">
              <label className="mb-1 block text-xs font-medium text-gray-500">
                {t('banking.direction')}
              </label>
              <Select value={direction} onValueChange={setDirection}>
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('banking.all')}</SelectItem>
                  <SelectItem value="debit">{t('banking.debit')}</SelectItem>
                  <SelectItem value="credit">{t('banking.credit')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Unmatched Credits */}
            <div className="flex items-end pb-1">
              <label className="inline-flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={unmatchedCredits}
                  onChange={(e) => setUnmatchedCredits(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                {t('banking.unmatchedCredits')}
              </label>
            </div>
          </div>

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
                        data-tx-id={tx.id}
                        className={`cursor-pointer hover:bg-gray-50 ${isExpanded ? 'bg-blue-50' : ''}`}
                        onClick={() => setExpandedTxId(isExpanded ? null : tx.id)}
                      >
                        <td className="whitespace-nowrap px-4 py-2.5 text-gray-900">
                          {formatDate(tx.entryDate)}
                        </td>
                        <td className="max-w-[220px] px-4 py-2.5 text-gray-900">
                          <div className="flex items-center gap-1">
                            <div className="min-w-0 flex-1 truncate">
                              {tx.counterparty?.name ? (
                                <Link
                                  to={`/banking/counterparty/${tx.counterparty.id}`}
                                  onClick={(e) => e.stopPropagation()}
                                  className="truncate text-blue-600 hover:text-blue-800 hover:underline"
                                >
                                  {tx.counterparty.name}
                                </Link>
                              ) : (
                                <span className="truncate">-</span>
                              )}
                            </div>
                            <Popover
                              open={editingTxCounterparty?.id === tx.id}
                              onOpenChange={(open) => {
                                if (open) {
                                  setEditingTxCounterparty(tx)
                                  setCpSearchQuery('')
                                  setShowCreateCp(false)
                                  setNewCpName('')
                                } else {
                                  setEditingTxCounterparty(null)
                                }
                              }}
                            >
                              <PopoverTrigger asChild>
                                <button
                                  onClick={(e) => e.stopPropagation()}
                                  className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                                  title={t('banking.editCounterparty')}
                                >
                                  <Pencil className="h-3.5 w-3.5" />
                                </button>
                              </PopoverTrigger>
                              <PopoverContent
                                className="w-[300px] p-0"
                                align="start"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {showCreateCp ? (
                                  <div className="p-3 space-y-3">
                                    <div className="text-sm font-medium">{t('banking.createCounterparty')}</div>
                                    <input
                                      type="text"
                                      placeholder={t('banking.counterpartyName')}
                                      value={newCpName}
                                      onChange={(e) => setNewCpName(e.target.value)}
                                      className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                                      autoFocus
                                    />
                                    <div className="flex gap-2">
                                      <button
                                        onClick={() => setShowCreateCp(false)}
                                        className="flex-1 rounded border px-3 py-1.5 text-sm hover:bg-gray-50"
                                      >
                                        {t('common.cancel')}
                                      </button>
                                      <button
                                        onClick={handleCreateAndSelectCounterparty}
                                        disabled={!newCpName.trim() || creatingCp}
                                        className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                                      >
                                        {creatingCp ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : t('common.create')}
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <Command shouldFilter={false}>
                                    <CommandInput
                                      placeholder={t('banking.searchCounterparty')}
                                      value={cpSearchQuery}
                                      onValueChange={setCpSearchQuery}
                                    />
                                    <CommandList>
                                      <CommandEmpty>{t('banking.noCounterpartiesFound')}</CommandEmpty>
                                      <CommandGroup>
                                        {searchedCounterparties.map((cp) => (
                                          <CommandItem
                                            key={cp.id}
                                            value={cp.id}
                                            onSelect={() => handleSelectCounterparty(cp.id)}
                                            disabled={updatingTxCp}
                                          >
                                            <div className="flex flex-col">
                                              <span>{cp.name}</span>
                                              {cp.iban && (
                                                <span className="text-xs text-gray-400">{cp.iban}</span>
                                              )}
                                            </div>
                                          </CommandItem>
                                        ))}
                                      </CommandGroup>
                                      <CommandSeparator />
                                      <CommandGroup>
                                        <CommandItem onSelect={() => setShowCreateCp(true)}>
                                          <Plus className="mr-2 h-4 w-4" />
                                          {t('banking.createNewCounterparty')}
                                        </CommandItem>
                                      </CommandGroup>
                                    </CommandList>
                                  </Command>
                                )}
                              </PopoverContent>
                            </Popover>
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
                            {tx.matchedInvoice && (
                              <Link
                                to={
                                  tx.matchedInvoice.contractId
                                    ? `/contracts/${tx.matchedInvoice.contractId}`
                                    : tx.matchedInvoice.customerId
                                    ? `/customers/${tx.matchedInvoice.customerId}`
                                    : '/invoices/imported'
                                }
                                onClick={(e) => e.stopPropagation()}
                                className="text-blue-600 hover:text-blue-800"
                                title={`${t('banking.matchedInvoice')}: ${tx.matchedInvoice.invoiceNumber}`}
                              >
                                <FileText className="h-4 w-4" />
                              </Link>
                            )}
                            {formatAmount(tx.amount, tx.currency)}
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

          {/* Pagination */}
          {totalCount > 0 && (
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
          </>
          )}
        </div>
      )}

      {/* Account Create/Edit Dialog */}
      <Dialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>
              {editingAccount ? t('banking.editAccount') : t('banking.addAccount')}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {t('banking.accountName')} *
              </label>
              <input
                type="text"
                value={accountForm.name}
                onChange={(e) => setAccountForm({ ...accountForm, name: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  {t('banking.bankCode')} *
                </label>
                <input
                  type="text"
                  value={accountForm.bankCode}
                  onChange={(e) => setAccountForm({ ...accountForm, bankCode: e.target.value })}
                  disabled={!!editingAccount}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  {t('banking.accountNumber')} *
                </label>
                <input
                  type="text"
                  value={accountForm.accountNumber}
                  onChange={(e) => setAccountForm({ ...accountForm, accountNumber: e.target.value })}
                  disabled={!!editingAccount}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
                />
              </div>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {t('banking.iban')}
              </label>
              <input
                type="text"
                value={accountForm.iban}
                onChange={(e) => setAccountForm({ ...accountForm, iban: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                {t('banking.bic')}
              </label>
              <input
                type="text"
                value={accountForm.bic}
                onChange={(e) => setAccountForm({ ...accountForm, bic: e.target.value })}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {accountError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {accountError}
              </div>
            )}
          </div>
          <DialogFooter>
            <button
              onClick={() => setAccountDialogOpen(false)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleSaveAccount}
              disabled={creating || updating}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {(creating || updating) && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('common.save')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteConfirmId !== null} onOpenChange={(open) => { if (!open) setDeleteConfirmId(null) }}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>{t('banking.deleteAccount')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">{t('banking.deleteConfirm')}</p>
          <DialogFooter>
            <button
              onClick={() => setDeleteConfirmId(null)}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleDeleteAccount}
              disabled={deleting}
              className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {deleting && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('common.delete')}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
