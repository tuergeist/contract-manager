import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import {
  Search,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertCircle,
} from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import { usePersistedState } from '@/lib/usePersistedState'

const OFFERS_QUERY = gql`
  query Offers(
    $search: String
    $status: String
    $sortBy: String
    $sortOrder: String
    $offset: Int
    $limit: Int
  ) {
    offers(
      search: $search
      status: $status
      sortBy: $sortBy
      sortOrder: $sortOrder
      offset: $offset
      limit: $limit
    ) {
      items {
        id
        offerNumber
        customerName
        customerId
        contractName
        contractId
        offerDate
        validUntil
        totalGross
        status
      }
      totalCount
      hasNextPage
    }
  }
`

const PAGE_SIZE = 20

interface OfferItem {
  id: number
  offerNumber: string
  customerName: string
  customerId: number | null
  contractName: string
  contractId: number | null
  offerDate: string
  validUntil: string | null
  totalGross: string
  status: string
}

function StatusBadge({ status, isExpired }: { status: string; isExpired: boolean }) {
  const { t } = useTranslation()

  if (isExpired && (status === 'draft' || status === 'sent')) {
    return (
      <Badge variant="destructive" className="text-xs">
        <AlertCircle className="w-3 h-3 mr-1" />
        {t('offers.statusExpired')}
      </Badge>
    )
  }

  const variants: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-blue-100 text-blue-700',
    accepted: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-500',
  }

  const labels: Record<string, string> = {
    draft: t('offers.statusDraft'),
    sent: t('offers.statusSent'),
    accepted: t('offers.statusAccepted'),
    rejected: t('offers.statusRejected'),
    cancelled: t('offers.statusCancelled'),
  }

  return (
    <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', variants[status] || variants.draft)}>
      {labels[status] || status}
    </span>
  )
}

export function OfferList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = usePersistedState<string>('cm:offerList:status', '')
  const [page, setPage] = useState(1)
  const [sortField, setSortField] = usePersistedState<string | null>('cm:offerList:sortField', null)
  const [sortOrder, setSortOrder] = usePersistedState<'asc' | 'desc'>('cm:offerList:sortOrder', 'desc')

  const { data, loading } = useQuery(OFFERS_QUERY, {
    variables: {
      search: search || null,
      status: statusFilter || null,
      sortBy: sortField,
      sortOrder: sortField ? sortOrder : null,
      offset: (page - 1) * PAGE_SIZE,
      limit: PAGE_SIZE,
    },
    fetchPolicy: 'cache-and-network',
  })

  const items: OfferItem[] = data?.offers?.items || []
  const totalCount = data?.offers?.totalCount || 0
  const hasNextPage = data?.offers?.hasNextPage || false
  const totalPages = Math.ceil(totalCount / PAGE_SIZE)
  const today = new Date().toISOString().slice(0, 10)

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

  const statusOptions = [
    { value: '', label: t('offers.allStatuses') },
    { value: 'draft', label: t('offers.statusDraft') },
    { value: 'sent', label: t('offers.statusSent') },
    { value: 'accepted', label: t('offers.statusAccepted') },
    { value: 'rejected', label: t('offers.statusRejected') },
    { value: 'cancelled', label: t('offers.statusCancelled') },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold">{t('offers.title')}</h1>
        <p className="text-sm text-gray-500">{t('offers.subtitle')}</p>
      </div>

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
            placeholder={t('offers.searchPlaceholder')}
            className="pl-9"
          />
        </div>
        <div className="inline-flex rounded-md border border-input overflow-hidden">
          {statusOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { setStatusFilter(opt.value); setPage(1) }}
              className={cn(
                'px-3 py-1.5 text-sm font-medium transition-colors',
                statusFilter === opt.value
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
            <tr className="border-b bg-gray-50">
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('offerNumber')}
              >
                {t('offers.colOfferNumber')}{getSortIcon('offerNumber')}
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('customerName')}
              >
                {t('offers.colCustomer')}{getSortIcon('customerName')}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {t('offers.colContract')}
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('offerDate')}
              >
                {t('offers.colOfferDate')}{getSortIcon('offerDate')}
              </th>
              <th
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('validUntil')}
              >
                {t('offers.colValidUntil')}{getSortIcon('validUntil')}
              </th>
              <th
                className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalGross')}
              >
                {t('offers.colTotalGross')}{getSortIcon('totalGross')}
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                {t('offers.colStatus')}
              </th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center">
                  <Loader2 className="w-6 h-6 mx-auto animate-spin text-gray-400" />
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                  {t('offers.noOffers')}
                </td>
              </tr>
            ) : (
              items.map((offer) => {
                const isExpired = offer.validUntil ? offer.validUntil < today : false
                return (
                  <tr
                    key={offer.id}
                    className="border-b hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/offers/${offer.id}`)}
                    data-testid={`offer-row-${offer.id}`}
                  >
                    <td className="px-4 py-3 text-sm font-medium">{offer.offerNumber}</td>
                    <td className="px-4 py-3 text-sm">{offer.customerName}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{offer.contractName}</td>
                    <td className="px-4 py-3 text-sm">{formatDate(offer.offerDate)}</td>
                    <td className={cn('px-4 py-3 text-sm', isExpired && (offer.status === 'draft' || offer.status === 'sent') && 'text-red-600')}>
                      {offer.validUntil ? formatDate(offer.validUntil) : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-medium">{formatCurrency(offer.totalGross)}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={offer.status} isExpired={isExpired} />
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {t('common.pagination.showing', {
              from: (page - 1) * PAGE_SIZE + 1,
              to: Math.min(page * PAGE_SIZE, totalCount),
              total: totalCount,
            })}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => p - 1)}
              disabled={page === 1}
              className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
              {t('common.pagination.previous')}
            </button>
            <span className="text-sm text-gray-500">
              {t('common.pagination.page', { page, totalPages })}
            </span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNextPage}
              className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {t('common.pagination.next')}
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
