import { useMemo, useState } from 'react'
import { usePersistedState } from '@/lib/usePersistedState'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  Loader2,
  CheckCircle2,
  CircleDot,
  FolderKanban,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  Search,
} from 'lucide-react'
import { formatDate, formatCurrency, formatNumber } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const DELIVERABLE_ITEMS_QUERY = gql`
  query DeliverableItems($status: String, $customerId: ID) {
    deliverableItems(status: $status, customerId: $customerId) {
      id
      productName
      description
      isOneOff
      deliveryStatus
      deliveredAt
      estimatedDeliveryDate
      contractId
      contractName
      customerName
      customerId
      dependentItemsCount
      hoursBooked
      orderValue
      orderConfirmationNumber
      psRatio
    }
  }
`

const MARK_ITEM_DELIVERED_MUTATION = gql`
  mutation MarkItemDelivered($itemId: ID!, $deliveredAt: Date!) {
    markItemDelivered(itemId: $itemId, deliveredAt: $deliveredAt) {
      success
      error
      dependentItems {
        id
        name
        hasBillingStartDate
      }
    }
  }
`

const SET_DELIVERABLE_ETA_MUTATION = gql`
  mutation SetDeliverableEta($itemId: ID!, $estimatedDeliveryDate: Date) {
    setDeliverableEta(itemId: $itemId, estimatedDeliveryDate: $estimatedDeliveryDate) {
      success
      error
    }
  }
`

const REVERT_ITEM_DELIVERY_MUTATION = gql`
  mutation RevertItemDelivery($itemId: ID!) {
    revertItemDelivery(itemId: $itemId) {
      success
      error
    }
  }
`

interface DeliverableItem {
  id: number
  productName: string | null
  description: string
  isOneOff: boolean
  deliveryStatus: string
  deliveredAt: string | null
  estimatedDeliveryDate: string | null
  contractId: number
  contractName: string
  customerName: string
  customerId: number
  dependentItemsCount: number
  hoursBooked: number
  orderValue: number
  orderConfirmationNumber: string | null
  psRatio: number | null
}

type SortField =
  | 'customer'
  | 'contract'
  | 'item'
  | 'ocNumber'
  | 'status'
  | 'eta'
  | 'hours'
  | 'orderValue'
  | 'psRatio'

type SortOrder = 'asc' | 'desc'

function itemLabel(item: DeliverableItem): string {
  return item.productName || item.description || ''
}

function etaSortValue(item: DeliverableItem): string {
  // Pending items sort by ETA, delivered by deliveredAt. Missing dates last.
  const v = item.deliveryStatus === 'delivered' ? item.deliveredAt : item.estimatedDeliveryDate
  return v || '9999-99-99'
}

function compareItems(a: DeliverableItem, b: DeliverableItem, field: SortField): number {
  switch (field) {
    case 'customer':
      return a.customerName.localeCompare(b.customerName)
    case 'contract':
      return a.contractName.localeCompare(b.contractName)
    case 'item':
      return itemLabel(a).localeCompare(itemLabel(b))
    case 'ocNumber':
      return (a.orderConfirmationNumber || '').localeCompare(b.orderConfirmationNumber || '')
    case 'status':
      return a.deliveryStatus.localeCompare(b.deliveryStatus)
    case 'eta':
      return etaSortValue(a).localeCompare(etaSortValue(b))
    case 'hours':
      return (a.hoursBooked || 0) - (b.hoursBooked || 0)
    case 'orderValue':
      return (a.orderValue || 0) - (b.orderValue || 0)
    case 'psRatio': {
      const av = a.psRatio == null ? -Infinity : a.psRatio
      const bv = b.psRatio == null ? -Infinity : b.psRatio
      return av - bv
    }
  }
}

function PsRatioCell({ value }: { value: number | null }) {
  if (value == null) {
    return <span className="text-gray-400">–</span>
  }
  const color =
    value >= 1 ? 'text-green-700' : value >= 0.8 ? 'text-amber-700' : 'text-red-700'
  return (
    <span className={`font-medium ${color}`}>
      {formatNumber(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
    </span>
  )
}

export function ProjectList() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = usePersistedState('cm:projectList:statusFilter', 'pending')
  const [searchTerm, setSearchTerm] = usePersistedState('cm:projectList:search', '')
  const [sortBy, setSortBy] = usePersistedState<SortField>('cm:projectList:sortBy', 'customer')
  const [sortOrder, setSortOrder] = usePersistedState<SortOrder>('cm:projectList:sortOrder', 'asc')
  const [deliveryItem, setDeliveryItem] = useState<DeliverableItem | null>(null)
  const [deliveryDate, setDeliveryDate] = useState(() => new Date().toISOString().slice(0, 10))

  const { data, loading, error, refetch } = useQuery(DELIVERABLE_ITEMS_QUERY, {
    variables: {
      status: statusFilter !== 'all' ? statusFilter : null,
    },
  })

  const [markDelivered] = useMutation(MARK_ITEM_DELIVERED_MUTATION)
  const [revertDelivery] = useMutation(REVERT_ITEM_DELIVERY_MUTATION)
  const [setEta] = useMutation(SET_DELIVERABLE_ETA_MUTATION)

  const items = (data?.deliverableItems || []) as DeliverableItem[]

  const filteredItems = useMemo(() => {
    const q = searchTerm.trim().toLowerCase()
    const filtered = q
      ? items.filter((i) => {
          return (
            i.customerName.toLowerCase().includes(q) ||
            i.contractName.toLowerCase().includes(q) ||
            itemLabel(i).toLowerCase().includes(q) ||
            (i.orderConfirmationNumber || '').toLowerCase().includes(q)
          )
        })
      : items
    const sorted = [...filtered].sort((a, b) => compareItems(a, b, sortBy))
    if (sortOrder === 'desc') sorted.reverse()
    return sorted
  }, [items, searchTerm, sortBy, sortOrder])

  const totals = useMemo(() => {
    return filteredItems.reduce(
      (acc, i) => {
        acc.hours += i.hoursBooked || 0
        acc.value += i.orderValue || 0
        return acc
      },
      { hours: 0, value: 0 }
    )
  }, [filteredItems])

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
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

  const handleMarkDelivered = async () => {
    if (!deliveryItem) return
    const result = await markDelivered({
      variables: { itemId: String(deliveryItem.id), deliveredAt: deliveryDate },
    })
    if (result.data?.markItemDelivered?.success) {
      setDeliveryItem(null)
      refetch()
    }
  }

  const handleSetEta = async (item: DeliverableItem, dateValue: string) => {
    await setEta({
      variables: {
        itemId: String(item.id),
        estimatedDeliveryDate: dateValue || null,
      },
    })
    refetch()
  }

  const handleRevertDelivery = async (item: DeliverableItem) => {
    if (!confirm(t('contracts.delivery.confirmRevert'))) return
    await revertDelivery({ variables: { itemId: String(item.id) } })
    refetch()
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-600">
        {error.message}
      </div>
    )
  }

  const thBase =
    'cursor-pointer px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100'
  const thBaseRight = thBase + ' text-right'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t('projects.title')}</h1>
        <div className="text-sm text-gray-500">
          {t('projects.totals', {
            count: filteredItems.length,
            hours: formatNumber(totals.hours, { maximumFractionDigits: 1 }),
            value: formatCurrency(totals.value),
          })}
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border bg-white p-4">
        <div className="flex flex-wrap items-end gap-4">
          <div className="w-48">
            <label className="mb-1 block text-xs font-medium text-gray-500">
              {t('projects.status')}
            </label>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pending">{t('contracts.delivery.pending')}</SelectItem>
                <SelectItem value="delivered">{t('contracts.delivery.delivered')}</SelectItem>
                <SelectItem value="all">{t('projects.allStatuses')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[16rem] flex-1">
            <label className="mb-1 block text-xs font-medium text-gray-500">
              {t('projects.search')}
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                className="pl-8"
                placeholder={t('projects.searchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {filteredItems.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <FolderKanban className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-600">{t('projects.noItems')}</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className={thBase} onClick={() => handleSort('customer')}>
                  <div className="flex items-center">
                    {t('projects.customer')}
                    <SortIcon field="customer" />
                  </div>
                </th>
                <th className={thBase} onClick={() => handleSort('contract')}>
                  <div className="flex items-center">
                    {t('projects.contract')}
                    <SortIcon field="contract" />
                  </div>
                </th>
                <th className={thBase} onClick={() => handleSort('item')}>
                  <div className="flex items-center">
                    {t('projects.item')}
                    <SortIcon field="item" />
                  </div>
                </th>
                <th className={thBase} onClick={() => handleSort('ocNumber')}>
                  <div className="flex items-center">
                    {t('projects.ocNumber')}
                    <SortIcon field="ocNumber" />
                  </div>
                </th>
                <th className={thBase} onClick={() => handleSort('status')}>
                  <div className="flex items-center">
                    {t('projects.status')}
                    <SortIcon field="status" />
                  </div>
                </th>
                <th className={thBase} onClick={() => handleSort('eta')}>
                  <div className="flex items-center">
                    {t('projects.eta')}
                    <SortIcon field="eta" />
                  </div>
                </th>
                <th className={thBaseRight} onClick={() => handleSort('hours')}>
                  <div className="flex items-center justify-end">
                    {t('projects.hours')}
                    <SortIcon field="hours" />
                  </div>
                </th>
                <th className={thBaseRight} onClick={() => handleSort('orderValue')}>
                  <div className="flex items-center justify-end">
                    {t('projects.orderValue')}
                    <SortIcon field="orderValue" />
                  </div>
                </th>
                <th className={thBaseRight} onClick={() => handleSort('psRatio')}>
                  <div className="flex items-center justify-end">
                    {t('projects.psRatio')}
                    <SortIcon field="psRatio" />
                  </div>
                </th>
                <th className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {filteredItems.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <Link
                      to={`/customers/${item.customerId}`}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {item.customerName}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <Link
                      to={`/contracts/${item.contractId}`}
                      className="font-medium text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {item.contractName || `#${item.contractId}`}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    <span className="font-medium text-gray-900">
                      {itemLabel(item) || '-'}
                    </span>
                    {item.dependentItemsCount > 0 && (
                      <span className="ml-2 text-xs text-gray-500">
                        {t('projects.dependentCount', { count: item.dependentItemsCount })}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {item.orderConfirmationNumber || <span className="text-gray-400">–</span>}
                  </td>
                  <td className="px-4 py-3">
                    {item.deliveryStatus === 'pending' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">
                        <CircleDot className="h-3 w-3" />
                        {t('contracts.delivery.pending')}
                      </span>
                    )}
                    {item.deliveryStatus === 'delivered' && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                        <CheckCircle2 className="h-3 w-3" />
                        {t('contracts.delivery.delivered')}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {item.deliveryStatus === 'pending' ? (
                      <Input
                        type="date"
                        className="h-8 w-40"
                        value={item.estimatedDeliveryDate || ''}
                        onChange={(e) => handleSetEta(item, e.target.value)}
                      />
                    ) : item.deliveredAt ? (
                      formatDate(item.deliveredAt)
                    ) : (
                      '-'
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-700">
                    {formatNumber(item.hoursBooked, { maximumFractionDigits: 1 })}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-700">
                    {formatCurrency(item.orderValue)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    <PsRatioCell value={item.psRatio} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right">
                    {item.deliveryStatus === 'pending' && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setDeliveryItem(item)
                          setDeliveryDate(new Date().toISOString().slice(0, 10))
                        }}
                      >
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        {t('contracts.delivery.markDelivered')}
                      </Button>
                    )}
                    {item.deliveryStatus === 'delivered' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRevertDelivery(item)}
                        className="text-gray-400 hover:text-amber-600"
                      >
                        {t('contracts.delivery.revertToPending')}
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={6} className="px-4 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('common.total', { defaultValue: 'Total' })}
                </td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-gray-900">
                  {formatNumber(totals.hours, { maximumFractionDigits: 1 })}
                </td>
                <td className="px-4 py-2 text-right text-sm font-semibold text-gray-900">
                  {formatCurrency(totals.value)}
                </td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* Mark Delivered Dialog */}
      <Dialog open={!!deliveryItem} onOpenChange={(open) => !open && setDeliveryItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('contracts.delivery.markDeliveredTitle')}</DialogTitle>
            <DialogDescription>
              {deliveryItem && (deliveryItem.productName || deliveryItem.description)}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium text-gray-700">{t('contracts.delivery.deliveredAt')}</label>
              <Input
                type="date"
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
                className="mt-1"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeliveryItem(null)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleMarkDelivered}>
              {t('contracts.delivery.markDelivered')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
