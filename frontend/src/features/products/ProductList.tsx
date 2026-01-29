import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, Search, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { usePersistedState } from '@/lib/usePersistedState'
import { formatDateTime } from '@/lib/utils'

const PRODUCTS_QUERY = gql`
  query Products($search: String, $page: Int, $pageSize: Int, $sortBy: String, $sortOrder: String) {
    products(search: $search, page: $page, pageSize: $pageSize, sortBy: $sortBy, sortOrder: $sortOrder) {
      items {
        id
        name
        sku
        description
        type
        isActive
        syncedAt
        category {
          id
          name
        }
        currentPrice {
          id
          price
          validFrom
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

interface ProductPrice {
  id: number
  price: string
  validFrom: string
}

interface ProductCategory {
  id: string
  name: string
}

interface Product {
  id: string
  name: string
  sku: string | null
  description: string | null
  type: string
  isActive: boolean
  syncedAt: string | null
  category: ProductCategory | null
  currentPrice: ProductPrice | null
}

interface ProductsData {
  products: {
    items: Product[]
    totalCount: number
    page: number
    pageSize: number
    hasNextPage: boolean
    hasPreviousPage: boolean
  }
}

type SortField = 'name' | 'sku' | 'price' | 'isActive' | 'syncedAt'
type SortOrder = 'asc' | 'desc'

const PAGE_SIZE = 20

export function ProductList() {
  const { t, i18n } = useTranslation()
  const [searchTerm, setSearchTerm] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = usePersistedState<SortField>('products-sort-by', 'name')
  const [sortOrder, setSortOrder] = usePersistedState<SortOrder>('products-sort-order', 'asc')

  const { data, loading, error } = useQuery<ProductsData>(PRODUCTS_QUERY, {
    variables: {
      search: searchTerm || null,
      page,
      pageSize: PAGE_SIZE,
      sortBy: sortBy === 'isActive' ? 'is_active' : sortBy === 'syncedAt' ? 'synced_at' : sortBy,
      sortOrder,
    },
  })

  const formatPrice = (price: string | null | undefined) => {
    if (!price) return '-'
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR'
    }).format(parseFloat(price))
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

  const productsData = data?.products
  const products = productsData?.items || []
  const totalCount = productsData?.totalCount || 0
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('products.title')}</h1>
        <span className="text-sm text-gray-500">
          {totalCount} {t('products.total')}
        </span>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mt-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t('products.searchPlaceholder')}
            className="w-full rounded-md border border-gray-300 py-2 pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </form>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-red-600">{error.message}</p>
        </div>
      ) : products.length === 0 ? (
        <p className="mt-4 text-gray-600">{t('products.noProducts')}</p>
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
                      {t('products.name')}
                      <SortIcon field="name" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('sku')}
                  >
                    <div className="flex items-center">
                      {t('products.sku')}
                      <SortIcon field="sku" />
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('products.category')}
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('price')}
                  >
                    <div className="flex items-center">
                      {t('products.price')}
                      <SortIcon field="price" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('isActive')}
                  >
                    <div className="flex items-center">
                      {t('products.status')}
                      <SortIcon field="isActive" />
                    </div>
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('syncedAt')}
                  >
                    <div className="flex items-center">
                      {t('products.syncedAt')}
                      <SortIcon field="syncedAt" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{product.name}</div>
                      {product.description && (
                        <div className="text-xs text-gray-500 line-clamp-1">{product.description}</div>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {product.sku || '-'}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {product.category?.name || '-'}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                      {formatPrice(product.currentPrice?.price)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                        product.isActive
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {product.isActive ? t('products.active') : t('products.inactive')}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDateTime(product.syncedAt)}
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
                  disabled={!productsData?.hasPreviousPage}
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
                  disabled={!productsData?.hasNextPage}
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
