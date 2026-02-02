import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, ArrowLeft, Building2, MapPin, FileText, ExternalLink, ArrowUpDown, ArrowUp, ArrowDown, History } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { formatDate, formatDateTime } from '@/lib/utils'
import { useAuditLogs, AuditLogTable } from '@/features/audit'

type SortField = 'name' | 'status' | 'startDate' | 'endDate' | 'arr' | 'totalValue' | 'remainingMonths' | null
type SortOrder = 'asc' | 'desc'

const CUSTOMER_QUERY = gql`
  query Customer($id: ID!) {
    customer(id: $id) {
      id
      name
      hubspotId
      hubspotUrl
      netsuiteCustomerNumber
      address
      isActive
      syncedAt
      createdAt
      contracts {
        id
        name
        status
        startDate
        endDate
        totalValue
        arr
        remainingMonths
      }
    }
  }
`

interface CustomerAddress {
  street?: string | null
  city?: string | null
  zip?: string | null
  country?: string | null
}

interface Contract {
  id: string
  name: string | null
  status: string
  startDate: string
  endDate: string | null
  totalValue: string
  arr: string
  remainingMonths: number
}

interface Customer {
  id: string
  name: string
  hubspotId: string | null
  hubspotUrl: string | null
  netsuiteCustomerNumber: string | null
  address: CustomerAddress | null
  isActive: boolean
  syncedAt: string | null
  createdAt: string
  contracts: Contract[]
}

interface CustomerData {
  customer: Customer | null
}

export function CustomerDetail() {
  const { id } = useParams<{ id: string }>()
  const { t, i18n } = useTranslation()
  const [sortField, setSortField] = useState<SortField>(null)
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  const { data, loading, error } = useQuery<CustomerData>(CUSTOMER_QUERY, {
    variables: { id },
    skip: !id,
  })

  const customer = data?.customer

  // Sort contracts
  const sortedContracts = useMemo(() => {
    if (!customer?.contracts) return []
    if (!sortField) return customer.contracts

    return [...customer.contracts].sort((a, b) => {
      let comparison = 0
      switch (sortField) {
        case 'name':
          comparison = (a.name || '').localeCompare(b.name || '', i18n.language)
          break
        case 'status':
          comparison = a.status.localeCompare(b.status, i18n.language)
          break
        case 'startDate':
          comparison = a.startDate.localeCompare(b.startDate)
          break
        case 'endDate':
          comparison = (a.endDate || '').localeCompare(b.endDate || '')
          break
        case 'arr':
          comparison = parseFloat(a.arr) - parseFloat(b.arr)
          break
        case 'totalValue':
          comparison = parseFloat(a.totalValue) - parseFloat(b.totalValue)
          break
        case 'remainingMonths':
          comparison = a.remainingMonths - b.remainingMonths
          break
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })
  }, [customer?.contracts, sortField, sortOrder, i18n.language])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      if (sortOrder === 'asc') {
        setSortOrder('desc')
      } else {
        setSortField(null)
        setSortOrder('asc')
      }
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 inline h-3 w-3 opacity-50" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="ml-1 inline h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 inline h-3 w-3" />
    )
  }

  const formatCurrency = (value: string | null) => {
    if (!value) return '-'
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(parseFloat(value))
  }

  const formatAddress = (address: CustomerAddress | null) => {
    if (!address) return null
    const parts = []
    if (address.street) parts.push(address.street)
    if (address.zip || address.city) {
      parts.push([address.zip, address.city].filter(Boolean).join(' '))
    }
    if (address.country) parts.push(address.country)
    return parts.length > 0 ? parts : null
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
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{error.message}</p>
      </div>
    )
  }

  if (!customer) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">{t('customers.notFound')}</p>
        <Link to="/customers" className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700">
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('common.back')}
        </Link>
      </div>
    )
  }

  const addressParts = formatAddress(customer.address)

  return (
    <div data-testid="customer-detail-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/customers" data-testid="customer-back-button">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold" data-testid="customer-name">{customer.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <span
                data-testid="customer-status-badge"
                className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
                  customer.isActive
                    ? 'bg-green-100 text-green-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {customer.isActive ? t('customers.active') : t('customers.inactive')}
              </span>
              {customer.netsuiteCustomerNumber && (
                <span className="text-sm text-gray-500">{customer.netsuiteCustomerNumber}</span>
              )}
              {customer.hubspotUrl && (
                <a
                  href={customer.hubspotUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-orange-600 hover:text-orange-800"
                >
                  <ExternalLink className="h-3 w-3" />
                  HubSpot
                </a>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Customer Info */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Address Card */}
        {addressParts && (
          <div className="rounded-lg border bg-white p-6">
            <div className="flex items-center gap-2 mb-4">
              <MapPin className="h-5 w-5 text-gray-400" />
              <h2 className="font-semibold">{t('customers.address')}</h2>
            </div>
            <div className="text-sm text-gray-600 space-y-1">
              {addressParts.map((part, index) => (
                <p key={index}>{part}</p>
              ))}
            </div>
          </div>
        )}

        {/* Info Card */}
        <div className="rounded-lg border bg-white p-6">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="h-5 w-5 text-gray-400" />
            <h2 className="font-semibold">{t('customers.info')}</h2>
          </div>
          <div className="text-sm space-y-2">
            <div className="flex justify-between">
              <span className="text-gray-500">{t('customers.createdAt')}</span>
              <span>{formatDateTime(customer.createdAt)}</span>
            </div>
            {customer.syncedAt && (
              <div className="flex justify-between">
                <span className="text-gray-500">{t('customers.syncedAt')}</span>
                <span>{formatDateTime(customer.syncedAt)}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Contracts Section */}
      <div className="mt-8" data-testid="customer-contracts-section">
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold">{t('contracts.title')}</h2>
          <span className="text-sm text-gray-500" data-testid="customer-contracts-count">
            ({customer.contracts.length})
          </span>
        </div>

        {customer.contracts.length === 0 ? (
          <div className="rounded-lg border bg-white p-8 text-center">
            <p className="text-gray-500">{t('customers.noContracts')}</p>
            <Link
              to="/contracts/new"
              className="mt-4 inline-flex items-center text-blue-600 hover:text-blue-700"
            >
              {t('contracts.newContract')}
            </Link>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('name')}
                  >
                    {t('contracts.form.name')}
                    {getSortIcon('name')}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('status')}
                  >
                    {t('contracts.statusLabel')}
                    {getSortIcon('status')}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('startDate')}
                  >
                    {t('contracts.startDate')}
                    {getSortIcon('startDate')}
                  </th>
                  <th
                    className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('endDate')}
                  >
                    {t('contracts.endDate')}
                    {getSortIcon('endDate')}
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('arr')}
                  >
                    {t('contracts.detail.arr')}
                    {getSortIcon('arr')}
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('totalValue')}
                  >
                    {t('contracts.value')}
                    {getSortIcon('totalValue')}
                  </th>
                  <th
                    className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('remainingMonths')}
                  >
                    {t('contracts.remainingMonths')}
                    {getSortIcon('remainingMonths')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {sortedContracts.map((contract) => (
                  <tr key={contract.id} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-6 py-4">
                      <Link
                        to={`/contracts/${contract.id}`}
                        className="font-medium text-blue-600 hover:text-blue-800"
                      >
                        {contract.name || '-'}
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
                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                      {formatCurrency(contract.arr)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                      {formatCurrency(contract.totalValue)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-500">
                      {contract.remainingMonths > 0 ? contract.remainingMonths : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Activity Section */}
      <div className="mt-8" data-testid="customer-activity-section">
        <div className="flex items-center gap-2 mb-4">
          <History className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold">{t('audit.activity')}</h2>
        </div>
        <CustomerActivityLog customerId={parseInt(id!, 10)} />
      </div>
    </div>
  )
}

function CustomerActivityLog({ customerId }: { customerId: number }) {
  const { t } = useTranslation()
  const { entries, totalCount, hasNextPage, loading, error, loadMore } = useAuditLogs({
    entityType: 'customer',
    entityId: customerId,
    includeRelated: false,
  })

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{error.message}</p>
      </div>
    )
  }

  return (
    <div>
      <AuditLogTable entries={entries} showEntity={false} loading={loading && entries.length === 0} />

      {hasNextPage && (
        <div className="mt-4 flex justify-center">
          <button
            onClick={loadMore}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('audit.loadMore')}
          </button>
        </div>
      )}

      {entries.length > 0 && (
        <div className="mt-4 text-center text-sm text-gray-500">
          {t('audit.showing', { count: entries.length, total: totalCount })}
        </div>
      )}
    </div>
  )
}
