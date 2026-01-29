import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  Loader2,
  ArrowLeft,
  Edit,
  Plus,
  Trash2,
  History,
  Package,
  FileText,
  ChevronsUpDown,
  Check,
  TrendingUp,
  ExternalLink,
  Lock,
  CalendarRange,
  Info,
} from 'lucide-react'
import { cn, formatDate, formatDateTime, formatMonthYear } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

const CONTRACT_DETAIL_QUERY = gql`
  query ContractDetail($id: ID!) {
    contract(id: $id) {
      id
      name
      status
      startDate
      endDate
      billingStartDate
      billingInterval
      billingAnchorDay
      minDurationMonths
      noticePeriodMonths
      noticePeriodAfterMinMonths
      noticePeriodAnchor
      cancelledAt
      cancellationEffectiveDate
      createdAt
      totalValue
      monthlyRecurringValue
      hubspotUrl
      netsuiteSalesOrderNumber
      netsuiteContractNumber
      poNumber
      discountAmount
      customer {
        id
        name
      }
      items {
        id
        description
        quantity
        unitPrice
        priceSource
        totalPrice
        startDate
        billingStartDate
        billingEndDate
        alignToContractAt
        suggestedAlignmentDate
        isOneOff
        priceLocked
        priceLockedUntil
        pricePeriods {
          id
          validFrom
          validTo
          unitPrice
          source
        }
        product {
          id
          name
          sku
        }
      }
      amendments {
        id
        effectiveDate
        type
        description
        createdAt
      }
    }
  }
`


const PRODUCTS_FOR_SELECT_QUERY = gql`
  query ProductsForSelect($search: String) {
    products(search: $search, page: 1, pageSize: 50, sortBy: "name", sortOrder: "asc") {
      items {
        id
        name
        sku
        currentPrice {
          price
        }
      }
    }
  }
`

const ADD_CONTRACT_ITEM_MUTATION = gql`
  mutation AddContractItem($contractId: ID!, $input: ContractItemInput!) {
    addContractItem(contractId: $contractId, input: $input) {
      success
      error
      item {
        id
      }
    }
  }
`

const UPDATE_CONTRACT_ITEM_MUTATION = gql`
  mutation UpdateContractItem($input: UpdateContractItemInput!) {
    updateContractItem(input: $input) {
      success
      error
    }
  }
`

const REMOVE_CONTRACT_ITEM_MUTATION = gql`
  mutation RemoveContractItem($itemId: ID!) {
    removeContractItem(itemId: $itemId) {
      success
      error
    }
  }
`

const SUGGESTED_ALIGNMENT_DATE_QUERY = gql`
  query SuggestedAlignmentDate($contractId: ID!, $billingStartDate: Date!) {
    suggestedAlignmentDate(contractId: $contractId, billingStartDate: $billingStartDate) {
      suggestedDate
      error
    }
  }
`

const ADD_CONTRACT_ITEM_PRICE_MUTATION = gql`
  mutation AddContractItemPrice($itemId: ID!, $input: ContractItemPriceInput!) {
    addContractItemPrice(itemId: $itemId, input: $input) {
      success
      error
      pricePeriod {
        id
        validFrom
        validTo
        unitPrice
        source
      }
    }
  }
`

const REMOVE_CONTRACT_ITEM_PRICE_MUTATION = gql`
  mutation RemoveContractItemPrice($priceId: ID!) {
    removeContractItemPrice(priceId: $priceId) {
      success
      error
    }
  }
`

const BILLING_SCHEDULE_QUERY = gql`
  query BillingSchedule($contractId: ID!, $months: Int, $includeHistory: Boolean) {
    billingSchedule(contractId: $contractId, months: $months, includeHistory: $includeHistory) {
      events {
        date
        items {
          itemId
          productName
          quantity
          unitPrice
          amount
          isProrated
          prorateFactor
        }
        total
      }
      totalForecast
      periodStart
      periodEnd
      error
    }
  }
`


interface Product {
  id: string
  name: string
  sku: string | null
  currentPrice: { price: string } | null
}

interface PricePeriod {
  id: string
  validFrom: string
  validTo: string | null
  unitPrice: string
  source: string
}

interface ContractItem {
  id: string
  description: string
  quantity: number
  unitPrice: string
  priceSource: string
  totalPrice: string
  startDate: string | null
  billingStartDate: string | null
  billingEndDate: string | null
  alignToContractAt: string | null
  suggestedAlignmentDate: string | null
  isOneOff: boolean
  priceLocked: boolean
  priceLockedUntil: string | null
  pricePeriods: PricePeriod[] | null
  product: {
    id: string
    name: string
    sku: string | null
  } | null
}

interface Amendment {
  id: string
  effectiveDate: string
  type: string
  description: string
  createdAt: string
}

interface Contract {
  id: string
  name: string
  status: string
  startDate: string
  endDate: string | null
  billingStartDate: string
  billingInterval: string
  billingAnchorDay: number
  minDurationMonths: number | null
  noticePeriodMonths: number
  noticePeriodAfterMinMonths: number | null
  noticePeriodAnchor: string
  cancelledAt: string | null
  cancellationEffectiveDate: string | null
  createdAt: string
  totalValue: string
  monthlyRecurringValue: string
  hubspotUrl: string | null
  netsuiteSalesOrderNumber: string | null
  netsuiteContractNumber: string | null
  poNumber: string | null
  discountAmount: string | null
  customer: {
    id: string
    name: string
  }
  items: ContractItem[]
  amendments: Amendment[]
}

type Tab = 'items' | 'amendments' | 'forecast'

export function ContractDetail() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('items')
  const [showAddItemModal, setShowAddItemModal] = useState(false)
  const [editingItem, setEditingItem] = useState<ContractItem | null>(null)
  
  const { data, loading, error, refetch } = useQuery(CONTRACT_DETAIL_QUERY, {
    variables: { id },
  })

  const contract = data?.contract as Contract | undefined

  const formatCurrency = (value: string | null) => {
    if (!value) return '-'
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(parseFloat(value))
  }

  const getIntervalMultiplier = (interval: string): number => {
    switch (interval) {
      case 'monthly': return 1
      case 'quarterly': return 3
      case 'semi_annual': return 6
      case 'annual': return 12
      default: return 1
    }
  }

  const formatARR = (monthlyValue: string | null): string => {
    if (!monthlyValue) return '-'
    const arr = parseFloat(monthlyValue) * 12
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(arr)
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

  if (error || !contract) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{error?.message || 'Contract not found'}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/contracts')}
            className="inline-flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('common.back')}
          </button>
          <div>
            <h1 className="text-2xl font-bold">
              {contract.name || contract.customer.name}
            </h1>
            <p className="text-sm text-muted-foreground">{contract.customer.name}</p>
            <div className="mt-1 flex items-center gap-2 flex-wrap">
              <span
                className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getStatusBadgeClass(
                  contract.status
                )}`}
              >
                {t(`contracts.status.${contract.status}`)}
              </span>
              {contract.netsuiteContractNumber && (
                <span className="text-xs text-gray-500">
                  {t('contracts.netsuiteContract')}: {contract.netsuiteContractNumber}
                </span>
              )}
              {contract.poNumber && (
                <span className="text-xs text-gray-500">
                  {t('contracts.poNumber')}: {contract.poNumber}
                </span>
              )}
              {contract.hubspotUrl && (
                <a
                  href={contract.hubspotUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-orange-600 hover:text-orange-800"
                >
                  <ExternalLink className="h-3 w-3" />
                  HubSpot
                </a>
              )}
            </div>
          </div>
        </div>
        {/* Details Button */}
        <Link to={`/contracts/${id}/edit`}>
          <Button variant="outline">
            {t('contracts.detail.details')}
          </Button>
        </Link>
      </div>

      {/* Overview Cards */}
      <div className="mb-6 grid gap-4 md:grid-cols-5">
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">{t('contracts.startDate')}</p>
          <p className="text-lg font-semibold">{formatDate(contract.startDate)}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">{t('contracts.endDate')}</p>
          <p className="text-lg font-semibold">{formatDate(contract.endDate)}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">{t('contracts.form.billingInterval')}</p>
          <p className="text-lg font-semibold">
            {t(`contracts.billingInterval.${contract.billingInterval}`)}
          </p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">{t('contracts.detail.arr')}</p>
          <p className="text-lg font-semibold">{formatARR(contract.monthlyRecurringValue)}</p>
        </div>
        <div className="rounded-lg border bg-white p-4">
          <p className="text-sm text-gray-500">{t('contracts.detail.totalValue')}</p>
          <p className="text-lg font-semibold">{formatCurrency(contract.totalValue)}</p>
        </div>
        {contract.discountAmount && parseFloat(contract.discountAmount) !== 0 && (
          <div className="rounded-lg border bg-white p-4">
            <p className="text-sm text-gray-500">{t('contracts.detail.discount')}</p>
            <p className="text-lg font-semibold text-red-600">{formatCurrency(contract.discountAmount)}</p>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-4 border-b">
        <nav className="-mb-px flex gap-4">
          <button
            onClick={() => setActiveTab('items')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'items'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <Package className="h-4 w-4" />
            {t('contracts.detail.items')} ({contract.items.length})
          </button>
          <button
            onClick={() => setActiveTab('amendments')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'amendments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <History className="h-4 w-4" />
            {t('contracts.detail.amendments')} ({contract.amendments.length})
          </button>
          <button
            onClick={() => setActiveTab('forecast')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'forecast'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <TrendingUp className="h-4 w-4" />
            {t('contracts.forecast.title')}
          </button>
        </nav>
      </div>

      {/* Items Tab */}
      {activeTab === 'items' && (
        <div>
          {contract.status !== 'cancelled' && contract.status !== 'ended' && (
            <div className="mb-4 flex justify-end">
              <button
                onClick={() => setShowAddItemModal(true)}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                {t('contracts.detail.addItem')}
              </button>
            </div>
          )}

          {contract.items.length === 0 ? (
            <div className="rounded-lg border bg-white p-8 text-center">
              <FileText className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-gray-600">{t('contracts.detail.noItems')}</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Recurring Items Table */}
              {contract.items.filter(item => !item.isOneOff).length > 0 && (
                <div className="overflow-hidden rounded-lg border">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.product')}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.quantity')}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.unitPriceMonthly')}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.totalMonthly')}
                        </th>
                        <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.totalBilling')}
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                          {t('contracts.item.billingPeriod')}
                        </th>
                        {contract.status !== 'cancelled' && contract.status !== 'ended' && (
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {/* Actions */}
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 bg-white">
                      {contract.items.filter(item => !item.isOneOff).map((item) => {
                        const monthlyTotal = parseFloat(item.totalPrice)
                        const intervalMultiplier = getIntervalMultiplier(contract.billingInterval)
                        const billingTotal = monthlyTotal * intervalMultiplier
                        const itemName = item.product?.name || item.description || '-'

                        return (
                          <tr key={item.id}>
                            <td className="px-6 py-4">
                              <span className="font-medium text-gray-900">{itemName}</span>
                              {item.product?.sku && (
                                <div className="text-xs text-gray-500">{item.product.sku}</div>
                              )}
                              {item.product && item.description && (
                                <div className="text-xs text-gray-500">{item.description}</div>
                              )}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                              {item.quantity}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                              <div className="flex items-center justify-end gap-1">
                                {item.priceLocked && (
                                  <span title={item.priceLockedUntil ? `${t('contracts.item.priceLockedUntil')}: ${formatDate(item.priceLockedUntil)}` : t('contracts.item.priceLocked')}>
                                    <Lock className="h-3 w-3 text-amber-500" />
                                  </span>
                                )}
                                {formatCurrency(item.unitPrice)}
                                {item.pricePeriods && item.pricePeriods.length > 0 && (
                                  <span title={t('contracts.item.yearSpecificPricing')}>
                                    <CalendarRange className="h-3 w-3 text-blue-500" />
                                  </span>
                                )}
                              </div>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                              {formatCurrency(item.totalPrice)}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                              {formatCurrency(billingTotal.toString())}
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-500">
                              {item.billingStartDate ? (
                                <div>
                                  <div>
                                    {formatDate(item.billingStartDate)} - {item.billingEndDate ? formatDate(item.billingEndDate) : t('contracts.item.ongoing')}
                                  </div>
                                  <div className="text-xs text-gray-400">
                                    {t(`contracts.billingInterval.${contract.billingInterval}`)}
                                  </div>
                                  {item.alignToContractAt && (
                                    <div className="text-xs text-gray-400">
                                      {t('contracts.item.alignsAt')}: {formatDate(item.alignToContractAt)}
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <span className="text-gray-400">-</span>
                              )}
                            </td>
                            {contract.status !== 'cancelled' && contract.status !== 'ended' && (
                              <td className="whitespace-nowrap px-6 py-4 text-right">
                                <button
                                  onClick={() => setEditingItem(item)}
                                  className="mr-2 text-gray-400 hover:text-blue-600"
                                >
                                  <Edit className="h-4 w-4" />
                                </button>
                                <RemoveItemButton
                                  itemId={item.id}
                                  itemName={itemName}
                                  onSuccess={() => refetch()}
                                />
                              </td>
                            )}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* One-Off Items Table */}
              {contract.items.filter(item => item.isOneOff).length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-medium text-gray-700">
                    {t('contracts.detail.oneOffItems')}
                  </h3>
                  <div className="overflow-hidden rounded-lg border">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.product')}
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.quantity')}
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.unitPriceShort')}
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.totalPriceShort')}
                          </th>
                          {contract.status !== 'cancelled' && contract.status !== 'ended' && (
                            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                              {/* Actions */}
                            </th>
                          )}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 bg-white">
                        {contract.items.filter(item => item.isOneOff).map((item) => {
                          const itemName = item.product?.name || item.description || '-'
                          return (
                          <tr key={item.id}>
                            <td className="px-6 py-4">
                              <span className="font-medium text-gray-900">{itemName}</span>
                              {item.product?.sku && (
                                <div className="text-xs text-gray-500">{item.product.sku}</div>
                              )}
                              {item.product && item.description && (
                                <div className="text-xs text-gray-500">{item.description}</div>
                              )}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                              {item.quantity}
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                              <div className="flex items-center justify-end gap-1">
                                {item.priceLocked && (
                                  <span title={item.priceLockedUntil ? `${t('contracts.item.priceLockedUntil')}: ${formatDate(item.priceLockedUntil)}` : t('contracts.item.priceLocked')}>
                                    <Lock className="h-3 w-3 text-amber-500" />
                                  </span>
                                )}
                                {formatCurrency(item.unitPrice)}
                              </div>
                            </td>
                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                              {formatCurrency(item.totalPrice)}
                            </td>
                            {contract.status !== 'cancelled' && contract.status !== 'ended' && (
                              <td className="whitespace-nowrap px-6 py-4 text-right">
                                <button
                                  onClick={() => setEditingItem(item)}
                                  className="mr-2 text-gray-400 hover:text-blue-600"
                                >
                                  <Edit className="h-4 w-4" />
                                </button>
                                <RemoveItemButton
                                  itemId={item.id}
                                  itemName={itemName}
                                  onSuccess={() => refetch()}
                                />
                              </td>
                            )}
                          </tr>
                        )})}

                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Amendments Tab */}
      {activeTab === 'amendments' && (
        <div>
          {contract.amendments.length === 0 ? (
            <div className="rounded-lg border bg-white p-8 text-center">
              <History className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-gray-600">{t('contracts.detail.noAmendments')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              {contract.amendments.map((amendment) => (
                <div key={amendment.id} className="rounded-lg border bg-white p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="inline-flex rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">
                        {t(`contracts.amendment.${amendment.type}`)}
                      </span>
                      <p className="mt-2 text-gray-900">{amendment.description}</p>
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      <p>{t('contracts.amendment.date')}: {formatDate(amendment.effectiveDate)}</p>
                      <p className="text-xs">{formatDateTime(amendment.createdAt)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Forecast Tab */}
      {activeTab === 'forecast' && (
        <ForecastTab contractId={id!} />
      )}

      {/* Add Item Modal */}
      {showAddItemModal && (
        <AddItemModal
          contractId={id!}
          onClose={() => setShowAddItemModal(false)}
          onSuccess={() => {
            setShowAddItemModal(false)
            refetch()
          }}
        />
      )}

      {/* Edit Item Modal */}
      {editingItem && (
        <EditItemModal
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onSuccess={() => {
            setEditingItem(null)
            refetch()
          }}
        />
      )}

    </div>
  )
}

// Sub-components for modals and actions

function AddItemModal({
  contractId,
  onClose,
  onSuccess,
}: {
  contractId: string
  onClose: () => void
  onSuccess: () => void
}) {
  const { t } = useTranslation()
  const [productId, setProductId] = useState('')
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState(1)
  const [unitPrice, setUnitPrice] = useState('')
  const [priceSource, setPriceSource] = useState('list')
  const [startDate, setStartDate] = useState('')
  const [billingStartDate, setBillingStartDate] = useState('')
  const [alignToContractAt, setAlignToContractAt] = useState('')
  const [isOneOff, setIsOneOff] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [productSearchOpen, setProductSearchOpen] = useState(false)
  const [productSearchTerm, setProductSearchTerm] = useState('')
  const billingStartManuallyChanged = useRef(false)

  const { data: productsData, loading: loadingProducts } = useQuery(PRODUCTS_FOR_SELECT_QUERY, {
    variables: { search: productSearchTerm || null },
  })

  const { data: suggestionData, loading: loadingSuggestion } = useQuery(SUGGESTED_ALIGNMENT_DATE_QUERY, {
    variables: { contractId, billingStartDate },
    skip: !billingStartDate,
  })

  const [addItem, { loading }] = useMutation(ADD_CONTRACT_ITEM_MUTATION)

  const products = (productsData?.products?.items || []) as Product[]
  const selectedProduct = products.find((p) => p.id === productId)
  const suggestedDate = suggestionData?.suggestedAlignmentDate?.suggestedDate

  // Auto-copy startDate to billingStartDate (one-time, can be manually changed)
  useEffect(() => {
    if (startDate && !billingStartManuallyChanged.current) {
      setBillingStartDate(startDate)
    }
  }, [startDate])

  const handleStartDateChange = (value: string) => {
    setStartDate(value)
  }

  const handleBillingStartDateManualChange = (value: string) => {
    billingStartManuallyChanged.current = true
    setBillingStartDate(value)
    // Clear alignment date when billing start changes
    setAlignToContractAt('')
  }

  const handleProductSelect = (id: string) => {
    setProductId(id)
    const product = products.find((p) => p.id === id)
    if (product?.currentPrice?.price) {
      setUnitPrice(product.currentPrice.price)
    }
    setProductSearchOpen(false)
  }

  const applySuggestedDate = () => {
    if (suggestedDate) {
      setAlignToContractAt(suggestedDate)
    }
  }

  const handleSubmit = async () => {
    setError(null)

    if (!productId && !description) {
      setError(t('contracts.item.productOrDescriptionRequired'))
      return
    }

    try {
      const result = await addItem({
        variables: {
          contractId,
          input: {
            productId: productId || null,
            description,
            quantity,
            unitPrice: unitPrice || '0',
            priceSource,
            startDate: startDate || null,
            billingStartDate: billingStartDate || null,
            alignToContractAt: alignToContractAt || null,
            isOneOff,
          },
        },
      })

      if (result.data?.addContractItem.success) {
        onSuccess()
      } else {
        setError(result.data?.addContractItem.error || 'Failed to add item')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{t('contracts.detail.addItem')}</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="space-y-4 py-4">
          {/* Searchable Product Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.product')}</label>
            <Popover open={productSearchOpen} onOpenChange={setProductSearchOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={productSearchOpen}
                  className="w-full justify-between"
                >
                  {selectedProduct ? (
                    <span>
                      {selectedProduct.name}
                      {selectedProduct.sku && (
                        <span className="ml-2 text-muted-foreground">({selectedProduct.sku})</span>
                      )}
                    </span>
                  ) : (
                    t('contracts.form.selectProduct')
                  )}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder={t('products.searchPlaceholder')}
                    value={productSearchTerm}
                    onValueChange={setProductSearchTerm}
                  />
                  <CommandList>
                    {loadingProducts && (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                    )}
                    <CommandEmpty>{t('products.noProducts')}</CommandEmpty>
                    <CommandGroup>
                      {products.map((product) => (
                        <CommandItem
                          key={product.id}
                          value={product.id}
                          onSelect={() => handleProductSelect(product.id)}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              productId === product.id ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          <div className="flex flex-col">
                            <span>{product.name}</span>
                            {product.sku && (
                              <span className="text-xs text-muted-foreground">{product.sku}</span>
                            )}
                          </div>
                          {product.currentPrice?.price && (
                            <span className="ml-auto text-sm text-muted-foreground">
                              {new Intl.NumberFormat('de-DE', {
                                style: 'currency',
                                currency: 'EUR',
                              }).format(parseFloat(product.currentPrice.price))}
                            </span>
                          )}
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.description')}</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('contracts.item.descriptionPlaceholder')}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              rows={2}
            />
            <p className="text-xs text-muted-foreground">
              {t('contracts.item.descriptionHint')}
            </p>
          </div>

          {/* Quantity */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.quantity')} *</label>
            <Input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
            />
          </div>

          {/* Unit Price */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.unitPrice')} *</label>
            <Input
              type="number"
              step="0.01"
              min="0"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
            />
          </div>

          {/* Price Source */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.priceSource')}</label>
            <Select value={priceSource} onValueChange={setPriceSource}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="list">{t('contracts.priceSource.list')}</SelectItem>
                <SelectItem value="custom">{t('contracts.priceSource.custom')}</SelectItem>
                <SelectItem value="customer_agreement">
                  {t('contracts.priceSource.customer_agreement')}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* One-Off Switch */}
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="isOneOff" className="text-sm font-medium">
                {t('contracts.item.isOneOff')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.isOneOffHint')}
              </p>
            </div>
            <Switch
              id="isOneOff"
              checked={isOneOff}
              onCheckedChange={setIsOneOff}
            />
          </div>

          {/* Start Date (effective date) */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.startDate')}</label>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => handleStartDateChange(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {t('contracts.item.startDateHint')}
            </p>
          </div>

          {/* Billing Start Date */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.billingStartDate')}</label>
            <Input
              type="date"
              value={billingStartDate}
              onChange={(e) => handleBillingStartDateManualChange(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {t('contracts.item.billingStartDateHint')}
            </p>
          </div>

          {/* Align to Contract At */}
          {billingStartDate && (
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.alignToContractAt')}</label>
              <div className="flex gap-2">
                <Input
                  type="date"
                  value={alignToContractAt}
                  onChange={(e) => setAlignToContractAt(e.target.value)}
                  className="flex-1"
                />
                {suggestedDate && !alignToContractAt && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={applySuggestedDate}
                    disabled={loadingSuggestion}
                    className="whitespace-nowrap"
                  >
                    {loadingSuggestion ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      formatDate(suggestedDate)
                    )}
                  </Button>
                )}
              </div>
              {suggestedDate && (
                <p className="text-xs text-muted-foreground">
                  {t('contracts.item.suggestedDate')}: {formatDate(suggestedDate)}
                </p>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('contracts.actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('common.create')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EditItemModal({
  item,
  onClose,
  onSuccess,
}: {
  item: ContractItem
  onClose: () => void
  onSuccess: () => void
}) {
  const { t, i18n } = useTranslation()
  const [description, setDescription] = useState(item.description || '')
  const [quantity, setQuantity] = useState(item.quantity)
  const [unitPrice, setUnitPrice] = useState(item.unitPrice)
  const [priceSource, setPriceSource] = useState(item.priceSource)
  const [startDate, setStartDate] = useState(item.startDate || '')
  const [billingStartDate, setBillingStartDate] = useState(item.billingStartDate || '')
  const [billingEndDate, setBillingEndDate] = useState(item.billingEndDate || '')
  const [alignToContractAt, setAlignToContractAt] = useState(item.alignToContractAt || '')
  const [isOneOff, setIsOneOff] = useState(item.isOneOff)
  const [priceLocked, setPriceLocked] = useState(item.priceLocked)
  const [priceLockedUntil, setPriceLockedUntil] = useState(item.priceLockedUntil || '')
  const [pricePeriods, setPricePeriods] = useState<PricePeriod[]>(item.pricePeriods || [])
  const [showPriceSchedule, setShowPriceSchedule] = useState((item.pricePeriods || []).length > 0)
  const [newPeriodFrom, setNewPeriodFrom] = useState('')
  const [newPeriodTo, setNewPeriodTo] = useState('')
  const [newPeriodPrice, setNewPeriodPrice] = useState('')
  const [newPeriodSource, setNewPeriodSource] = useState('fixed')
  const [error, setError] = useState<string | null>(null)

  const itemDisplayName = item.product?.name || item.description || `Item ${item.id}`

  const [updateItem, { loading }] = useMutation(UPDATE_CONTRACT_ITEM_MUTATION)
  const [addPricePeriodMutation, { loading: addingPeriod }] = useMutation(ADD_CONTRACT_ITEM_PRICE_MUTATION)
  const [removePricePeriodMutation, { loading: removingPeriod }] = useMutation(REMOVE_CONTRACT_ITEM_PRICE_MUTATION)

  const formatCurrencyLocal = (value: string | null) => {
    if (!value) return '-'
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(parseFloat(value))
  }

  const handleAddPricePeriod = async () => {
    if (!newPeriodFrom || !newPeriodPrice) return

    try {
      const result = await addPricePeriodMutation({
        variables: {
          itemId: item.id,
          input: {
            validFrom: newPeriodFrom,
            validTo: newPeriodTo || null,
            unitPrice: newPeriodPrice,
            source: newPeriodSource,
          },
        },
      })

      if (result.data?.addContractItemPrice.success) {
        const newPeriod = result.data.addContractItemPrice.pricePeriod
        setPricePeriods([...pricePeriods, newPeriod])
        setNewPeriodFrom('')
        setNewPeriodTo('')
        setNewPeriodPrice('')
        setNewPeriodSource('fixed')
      } else {
        setError(result.data?.addContractItemPrice.error || 'Failed to add price period')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const handleRemovePricePeriod = async (priceId: string) => {
    try {
      const result = await removePricePeriodMutation({
        variables: { priceId },
      })

      if (result.data?.removeContractItemPrice.success) {
        setPricePeriods(pricePeriods.filter(p => p.id !== priceId))
      } else {
        setError(result.data?.removeContractItemPrice.error || 'Failed to remove price period')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const handleSubmit = async () => {
    setError(null)

    try {
      const result = await updateItem({
        variables: {
          input: {
            id: item.id,
            description,
            quantity,
            unitPrice,
            priceSource,
            startDate: startDate || null,
            billingStartDate: billingStartDate || null,
            billingEndDate: billingEndDate || null,
            alignToContractAt: alignToContractAt || null,
            isOneOff,
            priceLocked,
            priceLockedUntil: priceLockedUntil || null,
          },
        },
      })

      if (result.data?.updateContractItem.success) {
        onSuccess()
      } else {
        setError(result.data?.updateContractItem.error || 'Failed to update item')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[900px]">
        <DialogHeader>
          <DialogTitle>{t('common.edit')}: {itemDisplayName}</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="space-y-4 py-4">
          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.description')}</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('contracts.item.descriptionPlaceholder')}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              rows={2}
            />
          </div>

          {/* Quantity, Unit Price, Price Source - 3 columns */}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.quantity')} *</label>
              <Input
                type="number"
                min={1}
                value={quantity}
                onChange={(e) => setQuantity(parseInt(e.target.value) || 1)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.unitPrice')} *</label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.priceSource')}</label>
              <Select value={priceSource} onValueChange={setPriceSource}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="list">{t('contracts.priceSource.list')}</SelectItem>
                  <SelectItem value="custom">{t('contracts.priceSource.custom')}</SelectItem>
                  <SelectItem value="customer_agreement">
                    {t('contracts.priceSource.customer_agreement')}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Price Lock */}
          <div className="rounded-lg border p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="priceLockedEdit" className="text-sm font-medium flex items-center gap-1">
                  <Lock className="h-3 w-3" />
                  {t('contracts.item.priceLocked')}
                  <span title={t('contracts.item.priceLockedHint')}>
                    <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                  </span>
                </Label>
              </div>
              <Switch
                id="priceLockedEdit"
                checked={priceLocked}
                onCheckedChange={setPriceLocked}
              />
            </div>
            {priceLocked && (
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('contracts.item.priceLockedUntil')}</label>
                <Input
                  type="date"
                  value={priceLockedUntil}
                  onChange={(e) => setPriceLockedUntil(e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Price Schedule */}
          <div className="rounded-lg border p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="showPriceSchedule" className="text-sm font-medium flex items-center gap-1">
                  <CalendarRange className="h-3 w-3" />
                  {t('contracts.item.yearSpecificPricing')}
                </Label>
                <p className="text-xs text-muted-foreground">
                  {t('contracts.item.yearSpecificPricingHint')}
                </p>
              </div>
              <Switch
                id="showPriceSchedule"
                checked={showPriceSchedule}
                onCheckedChange={setShowPriceSchedule}
              />
            </div>

            {showPriceSchedule && (
              <div className="space-y-3">
                {/* Existing Price Periods */}
                {pricePeriods.length > 0 ? (
                  <div className="space-y-2">
                    {pricePeriods.map((period) => (
                      <div key={period.id} className="flex items-center justify-between rounded border bg-gray-50 p-2 text-sm">
                        <div className="flex items-center gap-4">
                          <span>{formatMonthYear(period.validFrom)}</span>
                          <span className="text-gray-400">→</span>
                          <span>{period.validTo ? formatMonthYear(period.validTo) : t('contracts.item.ongoing')}</span>
                          <span className="font-medium">{formatCurrencyLocal(period.unitPrice)}</span>
                          <span className="text-xs text-gray-500">{t(`contracts.item.source${period.source.charAt(0).toUpperCase() + period.source.slice(1)}`)}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemovePricePeriod(period.id)}
                          disabled={removingPeriod}
                          className="text-gray-400 hover:text-red-600"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-2">{t('contracts.item.noPricePeriods')}</p>
                )}

                {/* Add New Price Period */}
                <div className="grid grid-cols-4 gap-2 pt-2 border-t">
                  <div>
                    <label className="text-xs text-gray-500">{t('contracts.item.periodFrom')}</label>
                    <Input
                      type="month"
                      value={newPeriodFrom ? newPeriodFrom.substring(0, 7) : ''}
                      onChange={(e) => setNewPeriodFrom(e.target.value ? `${e.target.value}-01` : '')}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">{t('contracts.item.periodTo')}</label>
                    <Input
                      type="month"
                      value={newPeriodTo ? newPeriodTo.substring(0, 7) : ''}
                      onChange={(e) => setNewPeriodTo(e.target.value ? `${e.target.value}-01` : '')}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">{t('contracts.item.periodPrice')}</label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={newPeriodPrice}
                      onChange={(e) => setNewPeriodPrice(e.target.value)}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">{t('contracts.item.periodSource')}</label>
                    <Select value={newPeriodSource} onValueChange={setNewPeriodSource}>
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fixed">{t('contracts.item.sourceFixed')}</SelectItem>
                        <SelectItem value="list">{t('contracts.item.sourceList')}</SelectItem>
                        <SelectItem value="negotiated">{t('contracts.item.sourceNegotiated')}</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddPricePeriod}
                  disabled={addingPeriod || !newPeriodFrom || !newPeriodPrice}
                  className="w-full"
                >
                  {addingPeriod && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                  <Plus className="mr-1 h-3 w-3" />
                  {t('contracts.item.addPricePeriod')}
                </Button>
              </div>
            )}
          </div>

          {/* One-Off Switch */}
          <div className="flex items-center justify-between rounded-lg border p-3">
            <div className="space-y-0.5">
              <Label htmlFor="isOneOffEdit" className="text-sm font-medium">
                {t('contracts.item.isOneOff')}
              </Label>
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.isOneOffHint')}
              </p>
            </div>
            <Switch
              id="isOneOffEdit"
              checked={isOneOff}
              onCheckedChange={setIsOneOff}
            />
          </div>

          {/* Start Date + Billing Start Date - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.startDate')}</label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.billingStartDate')}</label>
              <Input
                type="date"
                value={billingStartDate}
                onChange={(e) => setBillingStartDate(e.target.value)}
              />
            </div>
          </div>

          {/* Billing End Date + Align to Contract At - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.billingEndDate')}</label>
              <Input
                type="date"
                value={billingEndDate}
                onChange={(e) => setBillingEndDate(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.billingEndDateHint')}
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.alignToContractAt')}</label>
              <Input
                type="date"
                value={alignToContractAt}
                onChange={(e) => setAlignToContractAt(e.target.value)}
              />
              {item.suggestedAlignmentDate && (
                <p className="text-xs text-muted-foreground">
                  {t('contracts.item.suggestedDate')}: {formatDate(item.suggestedAlignmentDate)}
                </p>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('contracts.actions.cancel')}
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RemoveItemButton({
  itemId,
  itemName,
  onSuccess,
}: {
  itemId: string
  itemName: string
  onSuccess: () => void
}) {
  const { t } = useTranslation()
  const [removeItem, { loading }] = useMutation(REMOVE_CONTRACT_ITEM_MUTATION)

  const handleRemove = async () => {
    if (!confirm(`${t('contracts.actions.delete')} "${itemName}"?`)) {
      return
    }

    try {
      const result = await removeItem({
        variables: { itemId },
      })

      if (result.data?.removeContractItem.success) {
        onSuccess()
      }
    } catch (err) {
      console.error('Failed to remove item:', err)
    }
  }

  return (
    <button
      onClick={handleRemove}
      disabled={loading}
      className="text-gray-400 hover:text-red-600 disabled:opacity-50"
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
    </button>
  )
}

interface BillingScheduleItem {
  itemId: number
  productName: string
  quantity: number
  unitPrice: string
  amount: string
  isProrated: boolean
  prorateFactor: string | null
}

interface BillingEvent {
  date: string
  items: BillingScheduleItem[]
  total: string
}

interface BillingScheduleResult {
  events: BillingEvent[]
  totalForecast: string
  periodStart: string
  periodEnd: string
  error: string | null
}

function ForecastTab({ contractId }: { contractId: string }) {
  const { t, i18n } = useTranslation()
  const [months, setMonths] = useState('13')
  const [includeHistory, setIncludeHistory] = useState(false)

  const { data, loading, error } = useQuery(BILLING_SCHEDULE_QUERY, {
    variables: {
      contractId,
      months: parseInt(months),
      includeHistory,
    },
  })

  const schedule = data?.billingSchedule as BillingScheduleResult | undefined

  const formatCurrency = (value: string) => {
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(parseFloat(value))
  }

  const formatPercent = (value: string) => {
    return new Intl.NumberFormat(i18n.language, {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(parseFloat(value))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || schedule?.error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{error?.message || schedule?.error}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Controls */}
      <div className="mb-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">{t('contracts.forecast.months')}:</label>
          <Select value={months} onValueChange={setMonths}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="6">6</SelectItem>
              <SelectItem value="12">12</SelectItem>
              <SelectItem value="13">13</SelectItem>
              <SelectItem value="24">24</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="includeHistory"
            checked={includeHistory}
            onChange={(e) => setIncludeHistory(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300"
          />
          <label htmlFor="includeHistory" className="text-sm">
            {t('contracts.forecast.includeHistory')}
          </label>
        </div>
      </div>

      {/* Results */}
      {!schedule?.events || schedule.events.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <TrendingUp className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-600">{t('contracts.forecast.noEvents')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Billing Events Table */}
          <div className="overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('contracts.forecast.billingDate')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('contracts.forecast.items')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('contracts.forecast.amount')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {schedule.events.map((event, eventIndex) => (
                  <tr key={eventIndex}>
                    <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                      {formatDate(event.date)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        {event.items.map((item, itemIndex) => (
                          <div key={itemIndex} className="text-sm">
                            <span className="text-gray-900">
                              {item.productName} × {item.quantity}
                            </span>
                            {item.isProrated && item.prorateFactor && (
                              <span className="ml-2 rounded bg-yellow-100 px-1.5 py-0.5 text-xs text-yellow-800">
                                {t('contracts.forecast.prorated')} ({formatPercent(item.prorateFactor)})
                              </span>
                            )}
                            <span className="ml-2 text-gray-500">
                              {formatCurrency(item.amount)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900">
                      {formatCurrency(event.total)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot className="bg-gray-50">
                <tr>
                  <td colSpan={2} className="px-6 py-3 text-right text-sm font-medium text-gray-900">
                    {t('contracts.forecast.totalForecast')}
                  </td>
                  <td className="whitespace-nowrap px-6 py-3 text-right text-sm font-bold text-gray-900">
                    {formatCurrency(schedule.totalForecast)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>

          {/* Period Info */}
          <p className="text-xs text-gray-500">
            {formatDate(schedule.periodStart)} – {formatDate(schedule.periodEnd)}
          </p>
        </div>
      )}
    </div>
  )
}
