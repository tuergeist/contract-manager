import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Link } from 'react-router-dom'
import { Loader2, Search, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

const CUSTOMERS_QUERY = gql`
  query Customers($search: String, $isActive: Boolean, $page: Int, $pageSize: Int, $sortBy: String, $sortOrder: String) {
    customers(search: $search, isActive: $isActive, page: $page, pageSize: $pageSize, sortBy: $sortBy, sortOrder: $sortOrder) {
      items {
        id
        name
        hubspotId
        address
        isActive
        syncedAt
      }
      totalCount
      page
      pageSize
      hasNextPage
      hasPreviousPage
    }
  }
`

interface CustomerAddress {
  street?: string | null
  city?: string | null
  zip?: string | null
  country?: string | null
}

interface Customer {
  id: string
  name: string
  hubspotId: string | null
  address: CustomerAddress | null
  isActive: boolean
  syncedAt: string | null
}

interface CustomersData {
  customers: {
    items: Customer[]
    totalCount: number
    page: number
    pageSize: number
    hasNextPage: boolean
    hasPreviousPage: boolean
  }
}

type SortField = 'name' | 'isActive' | 'syncedAt'
type SortOrder = 'asc' | 'desc'

const PAGE_SIZE = 20

export function CustomerList() {
  const { t, i18n } = useTranslation()
  const [searchTerm, setSearchTerm] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState<SortField>('name')
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')
  const [showOnlyActive, setShowOnlyActive] = useState(true)

  const { data, loading, error } = useQuery<CustomersData>(CUSTOMERS_QUERY, {
    variables: {
      search: searchTerm || null,
      isActive: showOnlyActive ? true : null,
      page,
      pageSize: PAGE_SIZE,
      sortBy: sortBy === 'isActive' ? 'is_active' : sortBy === 'syncedAt' ? 'synced_at' : sortBy,
      sortOrder,
    },
  })

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString(i18n.language)
  }

  const formatAddress = (address: CustomerAddress | null) => {
    if (!address) return '-'
    const parts = [address.street, address.zip, address.city, address.country].filter(Boolean)
    return parts.length > 0 ? parts.join(', ') : '-'
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchTerm(searchInput)
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
    return sortOrder === 'asc'
      ? <ArrowUp className="ml-1 h-4 w-4" />
      : <ArrowDown className="ml-1 h-4 w-4" />
  }

  const customersData = data?.customers
  const customers = customersData?.items || []
  const totalCount = customersData?.totalCount || 0
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('customers.title')}</h1>
        <span className="text-sm text-gray-500">
          {totalCount} {t('customers.total')}
        </span>
      </div>

      {/* Search and Filter */}
      <div className="mt-4 flex items-center gap-4">
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder={t('customers.searchPlaceholder')}
              className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </form>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={showOnlyActive}
            onChange={(e) => {
              setShowOnlyActive(e.target.checked)
              setPage(1)
            }}
            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          {t('customers.showOnlyActive')}
        </label>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-red-600">{error.message}</p>
        </div>
      ) : customers.length === 0 ? (
        <p className="mt-4 text-gray-600">{t('customers.noCustomers')}</p>
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
                      {t('customers.name')}
                      <SortIcon field="name" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('customers.address')}
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('isActive')}
                  >
                    <div className="flex items-center">
                      {t('customers.status')}
                      <SortIcon field="isActive" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('syncedAt')}
                  >
                    <div className="flex items-center">
                      {t('customers.syncedAt')}
                      <SortIcon field="syncedAt" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white" data-testid="customers-table-body">
                {customers.map((customer) => (
                  <tr key={customer.id} className="hover:bg-gray-50" data-testid={`customer-row-${customer.id}`}>
                    <td className="whitespace-nowrap px-6 py-4">
                      <Link
                        to={`/customers/${customer.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800"
                        data-testid={`customer-link-${customer.id}`}
                      >
                        {customer.name}
                      </Link>
                      {customer.address?.city && (
                        <div className="text-sm text-muted-foreground">{customer.address.city}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {formatAddress(customer.address)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                        customer.isActive
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {customer.isActive ? t('customers.active') : t('customers.inactive')}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDate(customer.syncedAt)}
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
                  disabled={!customersData?.hasPreviousPage}
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
                  disabled={!customersData?.hasNextPage}
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
