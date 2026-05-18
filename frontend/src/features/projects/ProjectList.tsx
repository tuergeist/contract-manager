import { useState } from 'react'
import { usePersistedState } from '@/lib/usePersistedState'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  Loader2,
  CheckCircle2,
  CircleDot,
  FolderKanban,
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

interface ContractGroup {
  contractId: number
  contractName: string
  customerId: number
  customerName: string
  items: DeliverableItem[]
}

function groupByContract(items: DeliverableItem[]): ContractGroup[] {
  const groups = new Map<number, ContractGroup>()
  for (const item of items) {
    let group = groups.get(item.contractId)
    if (!group) {
      group = {
        contractId: item.contractId,
        contractName: item.contractName,
        customerId: item.customerId,
        customerName: item.customerName,
        items: [],
      }
      groups.set(item.contractId, group)
    }
    group.items.push(item)
  }
  return Array.from(groups.values())
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
  const groups = groupByContract(items)

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">{t('projects.title')}</h1>
      </div>

      {/* Filters */}
      <div className="rounded-lg border bg-white p-4">
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
      </div>

      {/* Grouped by contract */}
      {groups.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <FolderKanban className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-600">{t('projects.noItems')}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => {
            const totalHours = group.items.reduce((s, i) => s + (i.hoursBooked || 0), 0)
            const totalValue = group.items.reduce((s, i) => s + (i.orderValue || 0), 0)
            return (
              <div key={group.contractId} className="overflow-hidden rounded-lg border">
                {/* Contract group header */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-gray-50 px-6 py-3">
                  <div>
                    <Link
                      to={`/contracts/${group.contractId}`}
                      className="font-semibold text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {group.contractName || `#${group.contractId}`}
                    </Link>
                    <Link
                      to={`/customers/${group.customerId}`}
                      className="ml-2 text-xs text-gray-500 hover:text-blue-600"
                    >
                      {group.customerName}
                    </Link>
                  </div>
                  <div className="flex gap-6 text-xs text-gray-600">
                    <span>
                      {t('projects.hours')}:{' '}
                      <strong>{formatNumber(totalHours, { maximumFractionDigits: 1 })}</strong>
                    </span>
                    <span>
                      {t('projects.orderValue')}: <strong>{formatCurrency(totalValue)}</strong>
                    </span>
                  </div>
                </div>

                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-white">
                    <tr>
                      <th className="px-6 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.item')}
                      </th>
                      <th className="px-6 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.ocNumber')}
                      </th>
                      <th className="px-6 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.status')}
                      </th>
                      <th className="px-6 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.eta')}
                      </th>
                      <th className="px-6 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.hours')}
                      </th>
                      <th className="px-6 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.orderValue')}
                      </th>
                      <th className="px-6 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                        {t('projects.psRatio')}
                      </th>
                      <th className="px-6 py-2 text-right text-xs font-medium uppercase tracking-wider text-gray-500" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {group.items.map((item) => (
                      <tr key={item.id}>
                        <td className="px-6 py-3">
                          <span className="font-medium text-gray-900">
                            {item.productName || item.description || '-'}
                          </span>
                          {item.dependentItemsCount > 0 && (
                            <span className="ml-2 text-xs text-gray-500">
                              {t('projects.dependentCount', { count: item.dependentItemsCount })}
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-3 text-sm text-gray-700">
                          {item.orderConfirmationNumber || <span className="text-gray-400">–</span>}
                        </td>
                        <td className="px-6 py-3">
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
                        <td className="px-6 py-3 text-sm text-gray-500">
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
                        <td className="px-6 py-3 text-right text-sm text-gray-700">
                          {formatNumber(item.hoursBooked, { maximumFractionDigits: 1 })}
                        </td>
                        <td className="px-6 py-3 text-right text-sm text-gray-700">
                          {formatCurrency(item.orderValue)}
                        </td>
                        <td className="px-6 py-3 text-right text-sm">
                          <PsRatioCell value={item.psRatio} />
                        </td>
                        <td className="whitespace-nowrap px-6 py-3 text-right">
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
                </table>
              </div>
            )
          })}
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
