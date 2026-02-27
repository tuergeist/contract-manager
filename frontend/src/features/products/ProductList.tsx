import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Search, ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import { usePersistedState } from '@/lib/usePersistedState'
import { useAuth } from '@/lib/auth'
import { formatDateTime, formatCurrency } from '@/lib/utils'
import { HelpVideoButton } from '@/components/HelpVideoButton'

const PRODUCTS_QUERY = gql`
  query Products($search: String, $isActive: Boolean, $revenueType: String, $page: Int, $pageSize: Int, $sortBy: String, $sortOrder: String) {
    products(search: $search, isActive: $isActive, revenueType: $revenueType, page: $page, pageSize: $pageSize, sortBy: $sortBy, sortOrder: $sortOrder) {
      items {
        id
        name
        sku
        description
        type
        revenueType
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

const SET_PRODUCT_REVENUE_TYPE = gql`
  mutation SetProductRevenueType($productId: ID!, $revenueType: String!) {
    setProductRevenueType(productId: $productId, revenueType: $revenueType) {
      success
      error
      product {
        id
        revenueType
      }
    }
  }
`

const REVENUE_TYPE_OPTIONS = [
  { value: 'recurring', i18nKey: 'products.revenueTypes.recurring', bg: 'bg-green-100 text-green-800' },
  { value: 'advanced_development', i18nKey: 'products.revenueTypes.advancedDevelopment', bg: 'bg-orange-100 text-orange-800' },
  { value: 'training_implementation', i18nKey: 'products.revenueTypes.trainingImplementation', bg: 'bg-cyan-100 text-cyan-800' },
] as const

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
  revenueType: string | null
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

type SortField = 'name' | 'sku' | 'price' | 'isActive' | 'syncedAt' | 'revenueType'
type SortOrder = 'asc' | 'desc'

const PAGE_SIZE = 20

export function ProductList() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canEditProducts = hasPermission('products', 'write')
  const [searchTerm, setSearchTerm] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const [showInactive, setShowInactive] = useState(false)
  const [revenueTypeFilter, setRevenueTypeFilter] = useState<string>('')
  const [sortBy, setSortBy] = usePersistedState<SortField>('products-sort-by', 'name')
  const [sortOrder, setSortOrder] = usePersistedState<SortOrder>('products-sort-order', 'asc')
  const [editingProductId, setEditingProductId] = useState<string | null>(null)

  const [setProductRevenueType] = useMutation(SET_PRODUCT_REVENUE_TYPE)

  const { data, loading, error } = useQuery<ProductsData>(PRODUCTS_QUERY, {
    variables: {
      search: searchTerm || null,
      isActive: showInactive ? null : true,
      revenueType: revenueTypeFilter || null,
      page,
      pageSize: PAGE_SIZE,
      sortBy: sortBy === 'isActive' ? 'is_active' : sortBy === 'syncedAt' ? 'synced_at' : sortBy === 'revenueType' ? 'revenue_type' : sortBy,
      sortOrder,
    },
  })

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

  const handleRevenueTypeChange = async (productId: string, newRevenueType: string) => {
    setEditingProductId(null)
    await setProductRevenueType({
      variables: { productId, revenueType: newRevenueType },
      optimisticResponse: {
        setProductRevenueType: {
          __typename: 'SetProductRevenueTypeResult',
          success: true,
          error: null,
          product: { __typename: 'ProductType', id: productId, revenueType: newRevenueType },
        },
      },
    })
  }

  const productsData = data?.products
  const products = productsData?.items || []
  const totalCount = productsData?.totalCount || 0
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('products.title')}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500">
            {totalCount} {t('products.total')}
          </span>
          <HelpVideoButton />
        </div>
      </div>

      {/* Search and Filters */}
      <div className="mt-4 flex items-center gap-6">
        <form onSubmit={handleSearch} className="flex-1 max-w-md">
          <div className="relative">
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
        <select
          value={revenueTypeFilter}
          onChange={(e) => {
            setRevenueTypeFilter(e.target.value)
            setPage(1)
          }}
          className="rounded-md border border-gray-300 py-2 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">{t('products.allRevenueTypes')}</option>
          <option value="recurring">{t('products.revenueTypes.recurring')}</option>
          <option value="advanced_development">{t('products.revenueTypes.advancedDevelopment')}</option>
          <option value="training_implementation">{t('products.revenueTypes.trainingImplementation')}</option>
          <option value="unclassified">{t('products.revenueTypes.unclassified')}</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(e) => {
              setShowInactive(e.target.checked)
              setPage(1)
            }}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          {t('products.showInactive')}
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
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('products.type')}
                  </th>
                  <th
                    className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                    onClick={() => handleSort('revenueType')}
                  >
                    <div className="flex items-center">
                      {t('products.revenueType')}
                      <SortIcon field="revenueType" />
                    </div>
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
                    <td className="whitespace-nowrap px-6 py-4">
                      <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                        product.type === 'subscription'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-purple-100 text-purple-800'
                      }`}>
                        {product.type === 'subscription' ? t('products.subscription') : t('products.oneOff')}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4">
                      {editingProductId === product.id ? (
                        <select
                          autoFocus
                          defaultValue={product.revenueType || ''}
                          onChange={(e) => handleRevenueTypeChange(product.id, e.target.value)}
                          onBlur={() => setEditingProductId(null)}
                          className="rounded-md border border-blue-400 py-1 px-2 text-xs focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                        >
                          <option value="" disabled>{t('products.revenueTypes.unclassified')}</option>
                          {REVENUE_TYPE_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>{t(opt.i18nKey)}</option>
                          ))}
                        </select>
                      ) : product.revenueType ? (
                        <span
                          onClick={canEditProducts ? () => setEditingProductId(product.id) : undefined}
                          className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                            product.revenueType === 'recurring'
                              ? 'bg-green-100 text-green-800'
                              : product.revenueType === 'advanced_development'
                              ? 'bg-orange-100 text-orange-800'
                              : 'bg-cyan-100 text-cyan-800'
                          } ${canEditProducts ? 'cursor-pointer hover:ring-2 hover:ring-blue-300' : ''}`}
                        >
                          {t(`products.revenueTypes.${product.revenueType === 'advanced_development' ? 'advancedDevelopment' : product.revenueType === 'training_implementation' ? 'trainingImplementation' : 'recurring'}`)}
                        </span>
                      ) : (
                        <span
                          onClick={canEditProducts ? () => setEditingProductId(product.id) : undefined}
                          className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 bg-yellow-100 text-yellow-800 ${canEditProducts ? 'cursor-pointer hover:ring-2 hover:ring-blue-300' : ''}`}
                        >
                          {t('products.revenueTypes.unclassified')}
                        </span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                      {formatCurrency(product.currentPrice?.price)}
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
