import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import {
  ArrowLeft,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  X,
} from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const COUNTERPARTY_DETAIL = gql`
  query CounterpartyDetail($id: ID!) {
    counterparty(id: $id) {
      id
      name
      iban
      bic
      totalDebit
      totalCredit
      transactionCount
      firstDate
      lastDate
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
      }
      totalCount
      page
      pageSize
      hasNextPage
    }
  }
`

const BANK_ACCOUNTS = gql`
  query BankAccounts {
    bankAccounts {
      id
      name
    }
  }
`

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
}

export function CounterpartyDetailPage() {
  const { t } = useTranslation()
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // Expanded transaction row
  const [expandedTxId, setExpandedTxId] = useState<number | null>(null)

  // Filters
  const [filterAccountId, setFilterAccountId] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [amountMin, setAmountMin] = useState('')
  const [amountMax, setAmountMax] = useState('')
  const [direction, setDirection] = useState<string>('all')
  const [sortBy, setSortBy] = useState('date')
  const [sortOrder, setSortOrder] = useState('desc')
  const [page, setPage] = useState(1)
  const pageSize = 50

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300)
    return () => clearTimeout(timer)
  }, [searchQuery])

  useEffect(() => {
    setPage(1)
  }, [filterAccountId, debouncedSearch, dateFrom, dateTo, amountMin, amountMax, direction])

  // Counterparty detail query
  const { data: cpData, loading: cpLoading } = useQuery(COUNTERPARTY_DETAIL, {
    variables: { id },
    skip: !id,
  })

  const summary: CounterpartySummary | null = cpData?.counterparty || null

  // Transactions query
  const { data: txData, loading: txLoading } = useQuery(BANK_TRANSACTIONS, {
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

  // Accounts for filter dropdown
  const { data: accountsData } = useQuery(BANK_ACCOUNTS)
  const accounts = accountsData?.bankAccounts ?? []

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
    setPage(1)
  }

  const hasActiveFilters = filterAccountId !== 'all' || searchQuery || dateFrom || dateTo || amountMin || amountMax || direction !== 'all'

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

      {/* Page Title */}
      <h1 className="text-2xl font-bold text-gray-900">{summary?.name}</h1>

      {/* IBAN/BIC if available */}
      {(summary?.iban || summary?.bic) && (
        <p className="mt-1 text-sm text-gray-500">
          {summary?.iban && <span>{summary.iban}</span>}
          {summary?.iban && summary?.bic && <span> / </span>}
          {summary?.bic && <span>{summary.bic}</span>}
        </p>
      )}

      {/* Summary Cards - 4 in a row */}
      {summary && (
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">{t('banking.transactions')}</p>
            <p className="mt-1 text-xl font-semibold text-gray-900">{summary.transactionCount}</p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">{t('banking.totalDebit')}</p>
            <p className="mt-1 text-xl font-semibold text-red-600">
              {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(summary.totalDebit))}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">{t('banking.totalCredit')}</p>
            <p className="mt-1 text-xl font-semibold text-green-600">
              {new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(parseFloat(summary.totalCredit))}
            </p>
          </div>
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm font-medium text-gray-500">{t('banking.period')}</p>
            <p className="mt-1 text-xl font-semibold text-gray-900">
              {summary.firstDate && summary.lastDate
                ? `${formatDate(summary.firstDate)} – ${formatDate(summary.lastDate)}`
                : '-'}
            </p>
          </div>
        </div>
      )}

      {/* Transaction Table */}
      <div className="mt-6 space-y-4">
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
                {accounts.map((a: { id: number; name: string }) => (
                  <SelectItem key={a.id} value={String(a.id)}>
                    {a.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

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
                        {formatAmount(tx.amount, tx.currency)}
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
      </div>
    </div>
  )
}
