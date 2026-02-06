import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Link } from 'react-router-dom'
import {
  Loader2,
  Search,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Plus,
  Filter,
} from 'lucide-react'
import { usePersistedState } from '@/lib/usePersistedState'
import { formatDate } from '@/lib/utils'

const CONTRACTS_QUERY = gql`
  query Contracts(
    $search: String
    $status: String
    $page: Int
    $pageSize: Int
    $sortBy: String
    $sortOrder: String
  ) {
    contracts(
      search: $search
      status: $status
      page: $page
      pageSize: $pageSize
      sortBy: $sortBy
      sortOrder: $sortOrder
    ) {
      items {
        id
        name
        status
        startDate
        endDate
        updatedAt
        arr
        customer {
          id
          name
        }
      }
      totalCount
      page
      pageSize
      hasNextPage
      hasPreviousPage
    }
  }
`

interface Customer {
  id: string
  name: string
}

interface Contract {
  id: string
  name: string | null
  status: string
  startDate: string
  endDate: string | null
  updatedAt: string
  arr: string
  customer: Customer
}

interface ContractsData {
  contracts: {
    items: Contract[]
    totalCount: number
    page: number
    pageSize: number
    hasNextPage: boolean
    hasPreviousPage: boolean
  }
}

type SortField = 'name' | 'customer_name' | 'status' | 'start_date' | 'end_date' | 'arr' | 'updated_at'
type SortOrder = 'asc' | 'desc'

const PAGE_SIZE = 20

const CONTRACT_STATUSES = ['draft', 'active', 'paused', 'cancelled', 'ended', 'deleted'] as const

export function ContractList() {
  const { t, i18n } = useTranslation()
  const [searchTerm, setSearchTerm] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = usePersistedState<SortField>('contracts-sort-by', 'updated_at')
  const [sortOrder, setSortOrder] = usePersistedState<SortOrder>('contracts-sort-order', 'desc')

  const { data, loading, error } = useQuery<ContractsData>(CONTRACTS_QUERY, {
    variables: {
      search: searchTerm || null,
      status: statusFilter || null,
      page,
      pageSize: PAGE_SIZE,
      sortBy,
      sortOrder,
    },
  })

  const formatCurrency = (value: string | null) => {
    if (!value) return '-'
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(parseFloat(value))
  }

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'draft':
        return 'bg-yellow-100 text-yellow-800'
      case 'paused':
        return 'bg-blue-100 text-blue-800'
      case 'cancelled':
        return 'bg-red-100 text-red-800'
      case 'ended':
        return 'bg-gray-100 text-gray-800'
      case 'deleted':
        return 'bg-gray-200 text-gray-500 line-through'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchTerm(searchInput)
    setPage(1)
  }

  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setPage(1)
  }

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
    setPage(1)
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="ml-1 h-4 w-4 text-gray-400" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="ml-1 h-4 w-4" />
    ) : (
      <ArrowDown className="ml-1 h-4 w-4" />
    )
  }

  const contractsData = data?.contracts
  const contracts = contractsData?.items || []
  const totalCount = contractsData?.totalCount || 0
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('contracts.title')}</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-500">
            {totalCount} {t('contracts.total')}
          </span>
          <Link
            to="/contracts/new"
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('contracts.newContract')}
          </Link>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <form onSubmit={handleSearch} className="flex-1">
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t('contracts.searchPlaceholder')}
              className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </form>

        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-400" />
          <select
            value={statusFilter}
            onChange={(e) => handleStatusFilter(e.target.value)}
            className="rounded-md border border-gray-300 py-2 pl-3 pr-8 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">{t('contracts.allStatuses')}</option>
            {CONTRACT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {t(`contracts.status.${status}`)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-red-600">{error.message}</p>
        </div>
      ) : contracts.length === 0 ? (
        <div className="mt-8 text-center">
          <p className="text-gray-600">{t('contracts.noContracts')}</p>
          <Link
            to="/contracts/new"
            className="mt-4 inline-flex items-center gap-2 text-blue-600 hover:text-blue-700"
          >
            <Plus className="h-4 w-4" />
            {t('contracts.createFirst')}
          </Link>
        </div>
      ) : (
        <>
          <div className="mt-4 overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('name')}
                  >
                    <div className="flex items-center">
                      {t('contracts.form.name')}
                      <SortIcon field="name" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('customer_name')}
                  >
                    <div className="flex items-center">
                      {t('contracts.customer')}
                      <SortIcon field="customer_name" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('status')}
                  >
                    <div className="flex items-center">
                      {t('contracts.statusLabel')}
                      <SortIcon field="status" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('start_date')}
                  >
                    <div className="flex items-center">
                      {t('contracts.startDate')}
                      <SortIcon field="start_date" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('end_date')}
                  >
                    <div className="flex items-center">
                      {t('contracts.endDate')}
                      <SortIcon field="end_date" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('arr')}
                  >
                    <div className="flex items-center">
                      {t('contracts.arr')}
                      <SortIcon field="arr" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('updated_at')}
                  >
                    <div className="flex items-center">
                      {t('contracts.updatedAt')}
                      <SortIcon field="updated_at" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white" data-testid="contracts-table-body">
                {contracts.map((contract) => (
                  <tr key={contract.id} className="hover:bg-gray-50" data-testid={`contract-row-${contract.id}`}>
                    <td className="whitespace-nowrap px-6 py-4">
                      <Link
                        to={`/contracts/${contract.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800"
                        data-testid={`contract-link-${contract.id}`}
                      >
                        {contract.name || '-'}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                      <Link
                        to={`/customers/${contract.customer.id}`}
                        className="text-blue-600 hover:text-blue-800"
                        data-testid={`contract-customer-link-${contract.id}`}
                      >
                        {contract.customer.name}
                      </Link>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span
                        className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getStatusBadgeClass(
                          contract.status
                        )}`}
                      >
                        {t(`contracts.status.${contract.status}`)}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDate(contract.startDate)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDate(contract.endDate)}
                    </td>
                    <td className={`whitespace-nowrap px-6 py-4 text-sm font-medium ${contract.arr && parseFloat(contract.arr) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                      {formatCurrency(contract.arr)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDate(contract.updatedAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                {t('common.pagination.showing', {
                  from: (page - 1) * PAGE_SIZE + 1,
                  to: Math.min(page * PAGE_SIZE, totalCount),
                  total: totalCount,
                })}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={!contractsData?.hasPreviousPage}
                  className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <ChevronLeft className="h-4 w-4" />
                  {t('common.pagination.previous')}
                </button>
                <span className="text-sm text-gray-500">
                  {t('common.pagination.page', { page, totalPages })}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={!contractsData?.hasNextPage}
                  className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
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
  )
}
