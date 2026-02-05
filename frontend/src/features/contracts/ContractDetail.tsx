import { useState, useRef, useEffect, useMemo } from 'react'
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
  Paperclip,
  Upload,
  Download,
  File,
  Image,
  Eye,
  Link2,
  Clock,
  Scan,
  GripVertical,
} from 'lucide-react'
import { cn, formatDate, formatDateTime, formatMonthYear } from '@/lib/utils'
import { getToken } from '@/lib/auth'
import { useAuditLogs, AuditLogTable } from '@/features/audit'
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
import { TodoModal, TodoList, type TodoContext, type TodoItem } from '@/features/todos'
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { TimeTrackingTab } from './TimeTrackingTab'
import { PdfAnalysisPanel } from './PdfAnalysisPanel'
import { ListTodo } from 'lucide-react'

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
      netsuiteUrl
      notes
      invoiceText
      customer {
        id
        name
      }
      items {
        id
        description
        quantity
        unitPrice
        pricePeriod
        effectivePrice
        effectivePricePeriod
        priceSource
        totalPrice
        startDate
        billingStartDate
        billingEndDate
        alignToContractAt
        suggestedAlignmentDate
        isOneOff
        orderConfirmationNumber
        priceLocked
        priceLockedUntil
        sortOrder
        pricePeriods {
          id
          validFrom
          validTo
          unitPrice
          pricePeriod
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
      attachments {
        id
        originalFilename
        fileSize
        contentType
        description
        uploadedAt
        uploadedByName
        downloadUrl
      }
      links {
        id
        name
        url
        createdAt
        createdByName
      }
      todos {
        id
        text
        reminderDate
        isPublic
        isCompleted
        entityType
        entityName
        entityId
        createdById
        createdByName
        assignedToId
        assignedToName
        contractId
        contractItemId
        customerId
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
        isActive
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
        pricePeriod
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

const UPDATE_CONTRACT_ITEM_PRICE_MUTATION = gql`
  mutation UpdateContractItemPrice($input: UpdateContractItemPriceInput!) {
    updateContractItemPrice(input: $input) {
      success
      error
      pricePeriod {
        id
        validFrom
        validTo
        unitPrice
        pricePeriod
        source
      }
    }
  }
`

const UPDATE_CONTRACT_NOTES_MUTATION = gql`
  mutation UpdateContractNotes($input: UpdateContractInput!) {
    updateContract(input: $input) {
      success
      error
      contract {
        id
        notes
      }
    }
  }
`

const BILLING_SCHEDULE_QUERY = gql`
  query BillingSchedule($contractId: ID!, $months: Int, $includeAllHistory: Boolean) {
    billingSchedule(contractId: $contractId, months: $months, includeHistory: $includeAllHistory) {
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

const UPLOAD_ATTACHMENT_MUTATION = gql`
  mutation UploadContractAttachment($input: UploadAttachmentInput!) {
    uploadContractAttachment(input: $input) {
      success
      error
      attachment {
        id
        originalFilename
        fileSize
        contentType
        description
        uploadedAt
        uploadedByName
        downloadUrl
      }
    }
  }
`

const DELETE_ATTACHMENT_MUTATION = gql`
  mutation DeleteContractAttachment($attachmentId: ID!) {
    deleteContractAttachment(attachmentId: $attachmentId) {
      success
      error
    }
  }
`

const ADD_CONTRACT_LINK_MUTATION = gql`
  mutation AddContractLink($input: AddContractLinkInput!) {
    addContractLink(input: $input) {
      success
      error
      link {
        id
        name
        url
        createdAt
        createdByName
      }
    }
  }
`

const DELETE_CONTRACT_LINK_MUTATION = gql`
  mutation DeleteContractLink($linkId: ID!) {
    deleteContractLink(linkId: $linkId) {
      success
      error
    }
  }
`

const REORDER_CONTRACT_ITEMS_MUTATION = gql`
  mutation ReorderContractItems($input: ReorderContractItemsInput!) {
    reorderContractItems(input: $input) {
      success
      error
    }
  }
`


interface Product {
  id: string
  name: string
  sku: string | null
  isActive: boolean
  currentPrice: { price: string } | null
}

interface PricePeriod {
  id: string
  validFrom: string
  validTo: string | null
  unitPrice: string
  pricePeriod: string
  source: string
}

interface ContractItem {
  id: string
  description: string
  quantity: number
  unitPrice: string
  pricePeriod: string
  effectivePrice: string
  effectivePricePeriod: string
  priceSource: string
  totalPrice: string
  startDate: string | null
  billingStartDate: string | null
  billingEndDate: string | null
  alignToContractAt: string | null
  suggestedAlignmentDate: string | null
  isOneOff: boolean
  orderConfirmationNumber: string | null
  priceLocked: boolean
  priceLockedUntil: string | null
  sortOrder: number | null
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

interface Attachment {
  id: string
  originalFilename: string
  fileSize: number
  contentType: string
  description: string
  uploadedAt: string
  uploadedByName: string | null
  downloadUrl: string
}

interface ContractLink {
  id: string
  name: string
  url: string
  createdAt: string
  createdByName: string | null
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
  netsuiteUrl: string | null
  notes: string
  invoiceText: string
  customer: {
    id: string
    name: string
  }
  items: ContractItem[]
  amendments: Amendment[]
  attachments: Attachment[]
  links: ContractLink[]
  todos: TodoItem[]
}

function SortableRow({
  id,
  children,
  disabled,
}: {
  id: string
  children: (props: { dragHandleProps: React.HTMLAttributes<HTMLElement>; style: React.CSSProperties; ref: (node: HTMLElement | null) => void; isDragging: boolean }) => React.ReactNode
  disabled?: boolean
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    position: 'relative' as const,
    zIndex: isDragging ? 1 : 0,
  }

  const dragHandleProps = {
    ...attributes,
    ...listeners,
    style: { cursor: disabled ? 'default' : 'grab', touchAction: 'none' } as React.CSSProperties,
  }

  return <>{children({ dragHandleProps, style, ref: setNodeRef, isDragging })}</>
}

type Tab = 'items' | 'amendments' | 'forecast' | 'attachments' | 'todos' | 'timeTracking' | 'activity'

export function ContractDetail() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>('items')
  const [showAddItemModal, setShowAddItemModal] = useState(false)
  const [editingItem, setEditingItem] = useState<ContractItem | null>(null)
  const [isEditingNotes, setIsEditingNotes] = useState(false)
  const [editedNotes, setEditedNotes] = useState('')
  const [isEditingInvoiceText, setIsEditingInvoiceText] = useState(false)
  const [editedInvoiceText, setEditedInvoiceText] = useState('')
  const [todoModalOpen, setTodoModalOpen] = useState(false)
  const [todoContext, setTodoContext] = useState<TodoContext | undefined>()

  const { data, loading, error, refetch } = useQuery(CONTRACT_DETAIL_QUERY, {
    variables: { id },
  })

  const [updateNotes, { loading: savingNotes }] = useMutation(UPDATE_CONTRACT_NOTES_MUTATION)
  const [updateInvoiceText, { loading: savingInvoiceText }] = useMutation(UPDATE_CONTRACT_NOTES_MUTATION)
  const [reorderItems] = useMutation(REORDER_CONTRACT_ITEMS_MUTATION)

  const contract = data?.contract as Contract | undefined

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const canEdit = contract ? contract.status !== 'cancelled' && contract.status !== 'ended' : false

  const recurringItems = useMemo(
    () => contract?.items.filter(item => !item.isOneOff) || [],
    [contract?.items]
  )
  const oneOffItems = useMemo(
    () => contract?.items.filter(item => item.isOneOff) || [],
    [contract?.items]
  )

  const handleDragEnd = async (event: DragEndEvent, isOneOff: boolean) => {
    const { active, over } = event
    if (!over || active.id === over.id || !contract) return

    const items = isOneOff ? oneOffItems : recurringItems
    const oldIndex = items.findIndex(i => i.id === active.id)
    const newIndex = items.findIndex(i => i.id === over.id)
    if (oldIndex === -1 || newIndex === -1) return

    const reordered = arrayMove(items, oldIndex, newIndex)
    const itemIds = reordered.map(i => i.id)

    await reorderItems({
      variables: {
        input: {
          contractId: contract.id,
          itemIds,
          isOneOff,
        },
      },
    })
    refetch()
  }

  const handleSaveNotes = async () => {
    if (!contract) return
    const result = await updateNotes({
      variables: {
        input: {
          id: contract.id,
          notes: editedNotes,
        },
      },
    })
    if (result.data?.updateContract.success) {
      setIsEditingNotes(false)
      refetch()
    }
  }

  const handleStartEditNotes = () => {
    if (contract) {
      setEditedNotes(contract.notes || '')
      setIsEditingNotes(true)
    }
  }

  const handleSaveInvoiceText = async () => {
    if (!contract) return
    const result = await updateInvoiceText({
      variables: {
        input: {
          id: contract.id,
          invoiceText: editedInvoiceText,
        },
      },
    })
    if (result.data?.updateContract.success) {
      setIsEditingInvoiceText(false)
      refetch()
    }
  }

  const handleStartEditInvoiceText = () => {
    if (contract) {
      setEditedInvoiceText(contract.invoiceText || '')
      setIsEditingInvoiceText(true)
    }
  }

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
      case 'biennial': return 24
      case 'triennial': return 36
      case 'quadrennial': return 48
      case 'quinquennial': return 60
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
            <Link to={`/customers/${contract.customer.id}`} className="text-sm text-blue-600 hover:text-blue-800 hover:underline">
              {contract.customer.name}
            </Link>
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
              {contract.netsuiteSalesOrderNumber && (
                contract.netsuiteUrl ? (
                  <a
                    href={contract.netsuiteUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-800"
                  >
                    <ExternalLink className="h-3 w-3" />
                    SO: {contract.netsuiteSalesOrderNumber}
                  </a>
                ) : (
                  <span className="text-xs text-gray-500">
                    SO: {contract.netsuiteSalesOrderNumber}
                  </span>
                )
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
                  className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-800"
                >
                  <ExternalLink className="h-3 w-3" />
                  HubSpot
                </a>
              )}
            </div>
          </div>
        </div>
        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => {
              setTodoContext({
                type: 'contract',
                id: parseInt(id!),
                name: contract.name || contract.customer.name,
              })
              setTodoModalOpen(true)
            }}
          >
            <ListTodo className="mr-2 h-4 w-4" />
            {t('todos.addTodo')}
          </Button>
          <Link to={`/contracts/${id}/edit`}>
            <Button variant="outline">
              {t('contracts.detail.details')}
            </Button>
          </Link>
        </div>
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
      </div>

      {/* Internal Notes */}
      <div className="mb-6 rounded-lg border bg-white p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-medium text-gray-700">{t('contracts.detail.internalNotes')}</p>
          {!isEditingNotes && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleStartEditNotes}
              className="h-7 px-2"
            >
              <Edit className="h-3 w-3 mr-1" />
              {t('common.edit')}
            </Button>
          )}
        </div>
        {isEditingNotes ? (
          <div className="space-y-2">
            <textarea
              className="w-full rounded-md border border-gray-300 p-2 text-sm min-h-[100px] focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              value={editedNotes}
              onChange={(e) => setEditedNotes(e.target.value)}
              placeholder={t('contracts.detail.notesPlaceholder')}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditingNotes(false)}
              >
                {t('common.cancel')}
              </Button>
              <Button
                size="sm"
                onClick={handleSaveNotes}
                disabled={savingNotes}
              >
                {savingNotes && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                {t('common.save')}
              </Button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-600 whitespace-pre-wrap">
            {contract.notes || <span className="text-gray-400 italic">{t('contracts.detail.noNotes')}</span>}
          </p>
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
          <button
            onClick={() => setActiveTab('attachments')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'attachments'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <Paperclip className="h-4 w-4" />
            {t('attachments.title')} ({contract.attachments.length})
          </button>
          <button
            onClick={() => setActiveTab('todos')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'todos'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            } ${
              (contract.todos?.filter(t => !t.isCompleted).length || 0) > 0
                ? 'bg-yellow-100 rounded-t-md'
                : ''
            }`}
          >
            <ListTodo className="h-4 w-4" />
            {t('todos.title')} ({contract.todos?.filter(t => !t.isCompleted).length || 0})
          </button>
          <button
            onClick={() => setActiveTab('timeTracking')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'timeTracking'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <Clock className="h-4 w-4" />
            {t('timeTracking.title')}
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`inline-flex items-center gap-2 border-b-2 px-1 py-3 text-sm font-medium ${
              activeTab === 'activity'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
            }`}
          >
            <History className="h-4 w-4" />
            {t('audit.activity')}
          </button>
        </nav>
      </div>

      {/* Items Tab */}
      {activeTab === 'items' && (
        <div>
          {canEdit && (
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
              {recurringItems.length > 0 && (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={(event) => handleDragEnd(event, false)}
                >
                  <div className="overflow-hidden rounded-lg border">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          {canEdit && (
                            <th className="w-8 px-2 py-3" />
                          )}
                          <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.product')}
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.quantity')}
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                            {t('contracts.item.unitPrice')}
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
                          {canEdit && (
                            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                              {/* Actions */}
                            </th>
                          )}
                        </tr>
                      </thead>
                      <SortableContext items={recurringItems.map(i => i.id)} strategy={verticalListSortingStrategy}>
                        <tbody className="divide-y divide-gray-200 bg-white">
                          {recurringItems.map((item) => {
                            const effectivePrice = parseFloat(item.effectivePrice)
                            const pricePeriodMonths = getIntervalMultiplier(item.effectivePricePeriod)
                            const monthlyUnitPrice = effectivePrice / pricePeriodMonths
                            const monthlyTotal = monthlyUnitPrice * item.quantity
                            const intervalMultiplier = getIntervalMultiplier(contract.billingInterval)
                            const billingTotal = monthlyTotal * intervalMultiplier
                            const itemName = item.product?.name || item.description || '-'

                            return (
                              <SortableRow key={item.id} id={item.id} disabled={!canEdit}>
                                {({ dragHandleProps, style, ref }) => (
                                  <tr ref={ref} style={style}>
                                    {canEdit && (
                                      <td className="w-8 px-2 py-4">
                                        <span {...dragHandleProps} className="text-gray-400 hover:text-gray-600">
                                          <GripVertical className="h-4 w-4" />
                                        </span>
                                      </td>
                                    )}
                                    <td className="px-6 py-4">
                                      <span className="font-medium text-gray-900">{itemName}</span>
                                      {item.product?.sku && (
                                        <div className="text-xs text-gray-500">{item.product.sku}</div>
                                      )}
                                      {item.product && item.description && (
                                        <div className="text-xs text-gray-500 whitespace-pre-wrap">{item.description}</div>
                                      )}
                                    </td>
                                    <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                                      {item.quantity}
                                    </td>
                                    <td className={`whitespace-nowrap px-6 py-4 text-right text-sm ${parseFloat(item.effectivePrice) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                      <div className="flex items-center justify-end gap-1">
                                        {item.priceLocked && (
                                          <span title={item.priceLockedUntil ? `${t('contracts.item.priceLockedUntil')}: ${formatDate(item.priceLockedUntil)}` : t('contracts.item.priceLocked')}>
                                            <Lock className="h-3 w-3 text-amber-500" />
                                          </span>
                                        )}
                                        <span>
                                          {formatCurrency(item.effectivePrice)}
                                          <span className={`text-xs ${parseFloat(item.effectivePrice) < 0 ? 'text-red-400' : 'text-gray-500'}`}>
                                            /{t(`contracts.item.pricePeriodValues.${item.effectivePricePeriod}`)}
                                          </span>
                                        </span>
                                        {item.pricePeriods && item.pricePeriods.length > 0 && (
                                          <span title={t('contracts.item.yearSpecificPricing')}>
                                            <CalendarRange className="h-3 w-3 text-blue-500" />
                                          </span>
                                        )}
                                      </div>
                                    </td>
                                    <td className={`whitespace-nowrap px-6 py-4 text-right text-sm ${monthlyTotal < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                      {formatCurrency(monthlyTotal.toString())}
                                    </td>
                                    <td className={`whitespace-nowrap px-6 py-4 text-right text-sm font-medium ${billingTotal < 0 ? 'text-red-600' : 'text-gray-900'}`}>
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
                                    {canEdit && (
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
                                )}
                              </SortableRow>
                            )
                          })}
                        </tbody>
                      </SortableContext>
                    </table>
                  </div>
                </DndContext>
              )}

              {/* One-Off Items Table */}
              {oneOffItems.length > 0 && (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={(event) => handleDragEnd(event, true)}
                >
                  <div>
                    <h3 className="mb-2 text-sm font-medium text-gray-700">
                      {t('contracts.detail.oneOffItems')}
                    </h3>
                    <div className="overflow-hidden rounded-lg border">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
                            {canEdit && (
                              <th className="w-8 px-2 py-3" />
                            )}
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
                            {canEdit && (
                              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                                {/* Actions */}
                              </th>
                            )}
                          </tr>
                        </thead>
                        <SortableContext items={oneOffItems.map(i => i.id)} strategy={verticalListSortingStrategy}>
                          <tbody className="divide-y divide-gray-200 bg-white">
                            {oneOffItems.map((item) => {
                              const itemName = item.product?.name || item.description || '-'
                              const oneOffTotal = parseFloat(item.effectivePrice) * item.quantity
                              return (
                                <SortableRow key={item.id} id={item.id} disabled={!canEdit}>
                                  {({ dragHandleProps, style, ref }) => (
                                    <tr ref={ref} style={style}>
                                      {canEdit && (
                                        <td className="w-8 px-2 py-4">
                                          <span {...dragHandleProps} className="text-gray-400 hover:text-gray-600">
                                            <GripVertical className="h-4 w-4" />
                                          </span>
                                        </td>
                                      )}
                                      <td className="px-6 py-4">
                                        <span className="font-medium text-gray-900">{itemName}</span>
                                        {item.product?.sku && (
                                          <div className="text-xs text-gray-500">{item.product.sku}</div>
                                        )}
                                        {item.product && item.description && (
                                          <div className="text-xs text-gray-500 whitespace-pre-wrap">{item.description}</div>
                                        )}
                                      </td>
                                      <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-900">
                                        {item.quantity}
                                      </td>
                                      <td className={`whitespace-nowrap px-6 py-4 text-right text-sm ${parseFloat(item.effectivePrice) < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                        <div className="flex items-center justify-end gap-1">
                                          {item.priceLocked && (
                                            <span title={item.priceLockedUntil ? `${t('contracts.item.priceLockedUntil')}: ${formatDate(item.priceLockedUntil)}` : t('contracts.item.priceLocked')}>
                                              <Lock className="h-3 w-3 text-amber-500" />
                                            </span>
                                          )}
                                          <span>{formatCurrency(item.effectivePrice)}</span>
                                        </div>
                                      </td>
                                      <td className={`whitespace-nowrap px-6 py-4 text-right text-sm font-medium ${oneOffTotal < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                                        {formatCurrency(oneOffTotal.toString())}
                                      </td>
                                      {canEdit && (
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
                                  )}
                                </SortableRow>
                              )
                            })}
                          </tbody>
                        </SortableContext>
                      </table>
                    </div>
                  </div>
                </DndContext>
              )}

              {/* Invoice Text */}
              <div className="rounded-lg border bg-white p-4">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium text-gray-700">{t('contracts.detail.invoiceText')}</p>
                  {!isEditingInvoiceText && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleStartEditInvoiceText}
                      className="h-7 px-2"
                    >
                      <Edit className="h-3 w-3 mr-1" />
                      {t('common.edit')}
                    </Button>
                  )}
                </div>
                <p className="text-xs text-gray-500 mb-2">{t('contracts.detail.invoiceTextHint')}</p>
                {isEditingInvoiceText ? (
                  <div className="space-y-2">
                    <textarea
                      className="w-full rounded-md border border-gray-300 p-2 text-sm min-h-[100px] focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                      value={editedInvoiceText}
                      onChange={(e) => setEditedInvoiceText(e.target.value)}
                      placeholder={t('contracts.detail.invoiceTextPlaceholder')}
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsEditingInvoiceText(false)}
                      >
                        {t('common.cancel')}
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSaveInvoiceText}
                        disabled={savingInvoiceText}
                      >
                        {savingInvoiceText && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                        {t('common.save')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600 whitespace-pre-wrap">
                    {contract.invoiceText || <span className="text-gray-400 italic">{t('contracts.detail.noInvoiceText')}</span>}
                  </p>
                )}
              </div>
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

      {/* Attachments Tab */}
      {activeTab === 'attachments' && (
        <AttachmentsTab
          contractId={id!}
          attachments={contract.attachments}
          links={contract.links}
          canEdit={contract.status !== 'cancelled' && contract.status !== 'ended'}
          onRefetch={() => refetch()}
        />
      )}

      {/* Todos Tab */}
      {activeTab === 'todos' && (
        <div>
          <div className="mb-4 flex justify-end">
            <button
              onClick={() => {
                setTodoContext({
                  type: 'contract',
                  id: parseInt(id!),
                  name: contract.name || contract.customer.name,
                })
                setTodoModalOpen(true)
              }}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              {t('todos.addTodo')}
            </button>
          </div>
          <div className="rounded-lg border bg-white p-6">
            <TodoList
              todos={contract.todos || []}
              showCreator={true}
              onUpdate={() => refetch()}
            />
          </div>
        </div>
      )}

      {/* Time Tracking Tab */}
      {activeTab === 'timeTracking' && (
        <TimeTrackingTab contractId={id!} customerName={contract.customer.name} />
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <ActivityTab contractId={parseInt(id!, 10)} />
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

      {/* Todo Modal */}
      <TodoModal
        open={todoModalOpen}
        onOpenChange={setTodoModalOpen}
        context={todoContext}
        onSuccess={() => refetch()}
      />

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
  const [pricePeriod, setPricePeriod] = useState('monthly')
  const [priceSource, setPriceSource] = useState('list')
  const [startDate, setStartDate] = useState('')
  const [billingStartDate, setBillingStartDate] = useState('')
  const [alignToContractAt, setAlignToContractAt] = useState('')
  const [isOneOff, setIsOneOff] = useState(false)
  const [orderConfirmationNumber, setOrderConfirmationNumber] = useState('')
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

  // Sort products: active first, then by name
  const products = [...(productsData?.products?.items || []) as Product[]].sort((a, b) => {
    if (a.isActive !== b.isActive) return a.isActive ? -1 : 1
    return a.name.localeCompare(b.name)
  })
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
            pricePeriod,
            priceSource,
            startDate: startDate || null,
            billingStartDate: billingStartDate || null,
            alignToContractAt: alignToContractAt || null,
            isOneOff,
            orderConfirmationNumber: orderConfirmationNumber || null,
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
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{t('contracts.detail.addItem')}</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="space-y-4 py-4">
          {/* Product + Description - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
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
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.description')}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('contracts.item.descriptionPlaceholder')}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                rows={1}
              />
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.descriptionHint')}
              </p>
            </div>
          </div>

          {/* Quantity, Unit Price, Price Period, Price Source - 4 columns */}
          <div className="grid grid-cols-4 gap-4">
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
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.pricePeriod')}</label>
              <Select value={pricePeriod} onValueChange={setPricePeriod} disabled={isOneOff}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">{t('contracts.item.pricePeriodValues.monthly')}</SelectItem>
                  <SelectItem value="bi_monthly">{t('contracts.item.pricePeriodValues.bi_monthly')}</SelectItem>
                  <SelectItem value="quarterly">{t('contracts.item.pricePeriodValues.quarterly')}</SelectItem>
                  <SelectItem value="semi_annual">{t('contracts.item.pricePeriodValues.semi_annual')}</SelectItem>
                  <SelectItem value="annual">{t('contracts.item.pricePeriodValues.annual')}</SelectItem>
                  <SelectItem value="biennial">{t('contracts.item.pricePeriodValues.biennial')}</SelectItem>
                  <SelectItem value="triennial">{t('contracts.item.pricePeriodValues.triennial')}</SelectItem>
                  <SelectItem value="quadrennial">{t('contracts.item.pricePeriodValues.quadrennial')}</SelectItem>
                  <SelectItem value="quinquennial">{t('contracts.item.pricePeriodValues.quinquennial')}</SelectItem>
                </SelectContent>
              </Select>
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

          {/* One-Off + Order Confirmation - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
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
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.orderConfirmationNumber')}</label>
              <Input
                placeholder={t('contracts.item.orderConfirmationNumberPlaceholder')}
                value={orderConfirmationNumber}
                onChange={(e) => setOrderConfirmationNumber(e.target.value)}
              />
            </div>
          </div>

          {/* Start Date + Billing Start Date - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('contracts.item.startDate')}{' '}
                <span className="text-muted-foreground font-normal">{t('contracts.item.startDateSubtitle')}</span>
              </label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => handleStartDateChange(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.startDateHint')}
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('contracts.item.billingStartDate')}{' '}
                <span className="text-muted-foreground font-normal">{t('contracts.item.billingStartDateSubtitle')}</span>
              </label>
              <Input
                type="date"
                value={billingStartDate}
                onChange={(e) => handleBillingStartDateManualChange(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.billingStartDateHint')}
              </p>
            </div>
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
  const [productId, setProductId] = useState(item.product?.id || '')
  const [productSearchOpen, setProductSearchOpen] = useState(false)
  const [productSearchTerm, setProductSearchTerm] = useState('')
  const [description, setDescription] = useState(item.description || '')
  const [quantity, setQuantity] = useState(item.quantity)
  const [unitPrice, setUnitPrice] = useState(item.unitPrice)
  const [pricePeriodValue, setPricePeriodValue] = useState(item.pricePeriod || 'monthly')
  const [priceSource, setPriceSource] = useState(item.priceSource)
  const [startDate, setStartDate] = useState(item.startDate || '')
  const [billingStartDate, setBillingStartDate] = useState(item.billingStartDate || '')
  const [billingEndDate, setBillingEndDate] = useState(item.billingEndDate || '')
  const [alignToContractAt, setAlignToContractAt] = useState(item.alignToContractAt || '')
  const [isOneOff, setIsOneOff] = useState(item.isOneOff)
  const [orderConfirmationNumber, setOrderConfirmationNumber] = useState(item.orderConfirmationNumber || '')
  const [priceLocked, setPriceLocked] = useState(item.priceLocked)
  const [priceLockedUntil, setPriceLockedUntil] = useState(item.priceLockedUntil || '')
  const [pricePeriods, setPricePeriods] = useState<PricePeriod[]>(item.pricePeriods || [])
  const [showPriceSchedule, setShowPriceSchedule] = useState((item.pricePeriods || []).length > 0)
  const [newPeriodFrom, setNewPeriodFrom] = useState('')
  const [newPeriodTo, setNewPeriodTo] = useState('')
  const [newPeriodPrice, setNewPeriodPrice] = useState('')
  const [newPeriodPricePeriod, setNewPeriodPricePeriod] = useState('monthly')
  const [newPeriodSource, setNewPeriodSource] = useState('fixed')
  const [error, setError] = useState<string | null>(null)

  const { data: productsData, loading: loadingProducts } = useQuery(PRODUCTS_FOR_SELECT_QUERY, {
    variables: { search: productSearchTerm || null },
  })

  const products = [...(productsData?.products?.items || []) as Product[]].sort((a, b) => {
    if (a.isActive !== b.isActive) return a.isActive ? -1 : 1
    return a.name.localeCompare(b.name)
  })
  const selectedProduct = products.find((p) => p.id === productId) || (item.product ? { id: item.product.id, name: item.product.name, sku: item.product.sku, isActive: true, currentPrice: null } as Product : null)

  const handleProductSelect = (id: string) => {
    setProductId(id)
    const product = products.find((p) => p.id === id)
    if (product?.currentPrice?.price) {
      setUnitPrice(product.currentPrice.price)
    }
    setProductSearchOpen(false)
  }

  const itemDisplayName = item.product?.name || item.description || `Item ${item.id}`

  const [updateItem, { loading }] = useMutation(UPDATE_CONTRACT_ITEM_MUTATION)
  const [addPricePeriodMutation, { loading: addingPeriod }] = useMutation(ADD_CONTRACT_ITEM_PRICE_MUTATION)
  const [removePricePeriodMutation, { loading: removingPeriod }] = useMutation(REMOVE_CONTRACT_ITEM_PRICE_MUTATION)
  const [updatePricePeriodMutation, { loading: updatingPeriod }] = useMutation(UPDATE_CONTRACT_ITEM_PRICE_MUTATION)

  // State for editing an existing price period
  const [editingPeriodId, setEditingPeriodId] = useState<string | null>(null)
  const [editPeriodFrom, setEditPeriodFrom] = useState('')
  const [editPeriodTo, setEditPeriodTo] = useState('')
  const [editPeriodPrice, setEditPeriodPrice] = useState('')
  const [editPeriodPricePeriod, setEditPeriodPricePeriod] = useState('monthly')
  const [editPeriodSource, setEditPeriodSource] = useState('fixed')

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
            pricePeriod: newPeriodPricePeriod,
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
        setNewPeriodPricePeriod('monthly')
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

  const startEditingPeriod = (period: PricePeriod) => {
    setEditingPeriodId(period.id)
    setEditPeriodFrom(period.validFrom)
    setEditPeriodTo(period.validTo || '')
    setEditPeriodPrice(period.unitPrice)
    setEditPeriodPricePeriod(period.pricePeriod)
    setEditPeriodSource(period.source)
  }

  const cancelEditingPeriod = () => {
    setEditingPeriodId(null)
    setEditPeriodFrom('')
    setEditPeriodTo('')
    setEditPeriodPrice('')
    setEditPeriodPricePeriod('monthly')
    setEditPeriodSource('fixed')
  }

  const handleUpdatePricePeriod = async () => {
    if (!editingPeriodId || !editPeriodFrom || !editPeriodPrice) return

    try {
      const result = await updatePricePeriodMutation({
        variables: {
          input: {
            id: editingPeriodId,
            validFrom: editPeriodFrom,
            validTo: editPeriodTo || null,
            unitPrice: editPeriodPrice,
            pricePeriod: editPeriodPricePeriod,
            source: editPeriodSource,
          },
        },
      })

      if (result.data?.updateContractItemPrice.success) {
        const updatedPeriod = result.data.updateContractItemPrice.pricePeriod
        setPricePeriods(pricePeriods.map(p => p.id === editingPeriodId ? updatedPeriod : p))
        cancelEditingPeriod()
      } else {
        setError(result.data?.updateContractItemPrice.error || 'Failed to update price period')
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
            productId: productId || null,
            description,
            quantity,
            unitPrice,
            pricePeriod: pricePeriodValue,
            priceSource,
            startDate: startDate || null,
            billingStartDate: billingStartDate || null,
            billingEndDate: billingEndDate || null,
            alignToContractAt: alignToContractAt || null,
            isOneOff,
            orderConfirmationNumber: orderConfirmationNumber || null,
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
          {/* Product + Description - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
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
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.description')}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t('contracts.item.descriptionPlaceholder')}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                rows={1}
              />
              <p className="text-xs text-muted-foreground">
                {t('contracts.item.descriptionHint')}
              </p>
            </div>
          </div>

          {/* Quantity, Unit Price, Price Period, Price Source - 4 columns */}
          <div className="grid grid-cols-4 gap-4">
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
                value={unitPrice}
                onChange={(e) => setUnitPrice(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('contracts.item.pricePeriod')}</label>
              <Select value={pricePeriodValue} onValueChange={setPricePeriodValue} disabled={isOneOff}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly">{t('contracts.item.pricePeriodValues.monthly')}</SelectItem>
                  <SelectItem value="bi_monthly">{t('contracts.item.pricePeriodValues.bi_monthly')}</SelectItem>
                  <SelectItem value="quarterly">{t('contracts.item.pricePeriodValues.quarterly')}</SelectItem>
                  <SelectItem value="semi_annual">{t('contracts.item.pricePeriodValues.semi_annual')}</SelectItem>
                  <SelectItem value="annual">{t('contracts.item.pricePeriodValues.annual')}</SelectItem>
                  <SelectItem value="biennial">{t('contracts.item.pricePeriodValues.biennial')}</SelectItem>
                  <SelectItem value="triennial">{t('contracts.item.pricePeriodValues.triennial')}</SelectItem>
                  <SelectItem value="quadrennial">{t('contracts.item.pricePeriodValues.quadrennial')}</SelectItem>
                  <SelectItem value="quinquennial">{t('contracts.item.pricePeriodValues.quinquennial')}</SelectItem>
                </SelectContent>
              </Select>
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
                      <div key={period.id} className="rounded border bg-gray-50 p-2 text-sm">
                        {editingPeriodId === period.id ? (
                          /* Edit Mode */
                          <div className="space-y-2">
                            <div className="grid grid-cols-5 gap-2">
                              <div>
                                <label className="text-xs text-gray-500">{t('contracts.item.periodFrom')}</label>
                                <Input
                                  type="month"
                                  value={editPeriodFrom ? editPeriodFrom.substring(0, 7) : ''}
                                  onChange={(e) => setEditPeriodFrom(e.target.value ? `${e.target.value}-01` : '')}
                                  className="h-8 text-sm"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">{t('contracts.item.periodTo')}</label>
                                <Input
                                  type="month"
                                  value={editPeriodTo ? editPeriodTo.substring(0, 7) : ''}
                                  onChange={(e) => setEditPeriodTo(e.target.value ? `${e.target.value}-01` : '')}
                                  className="h-8 text-sm"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">{t('contracts.item.periodPrice')}</label>
                                <Input
                                  type="number"
                                  step="0.01"
                                  value={editPeriodPrice}
                                  onChange={(e) => setEditPeriodPrice(e.target.value)}
                                  className="h-8 text-sm"
                                />
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">{t('contracts.item.pricePeriod')}</label>
                                <Select value={editPeriodPricePeriod} onValueChange={setEditPeriodPricePeriod}>
                                  <SelectTrigger className="h-8 text-sm">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="monthly">{t('contracts.item.pricePeriodValues.monthly')}</SelectItem>
                                    <SelectItem value="bi_monthly">{t('contracts.item.pricePeriodValues.bi_monthly')}</SelectItem>
                                    <SelectItem value="quarterly">{t('contracts.item.pricePeriodValues.quarterly')}</SelectItem>
                                    <SelectItem value="semi_annual">{t('contracts.item.pricePeriodValues.semi_annual')}</SelectItem>
                                    <SelectItem value="annual">{t('contracts.item.pricePeriodValues.annual')}</SelectItem>
                                    <SelectItem value="biennial">{t('contracts.item.pricePeriodValues.biennial')}</SelectItem>
                                    <SelectItem value="triennial">{t('contracts.item.pricePeriodValues.triennial')}</SelectItem>
                                    <SelectItem value="quadrennial">{t('contracts.item.pricePeriodValues.quadrennial')}</SelectItem>
                                    <SelectItem value="quinquennial">{t('contracts.item.pricePeriodValues.quinquennial')}</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <div>
                                <label className="text-xs text-gray-500">{t('contracts.item.sourceLabel')}</label>
                                <Select value={editPeriodSource} onValueChange={setEditPeriodSource}>
                                  <SelectTrigger className="h-8 text-sm">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="fixed">{t('contracts.item.sourceFixed')}</SelectItem>
                                    <SelectItem value="increase">{t('contracts.item.sourceIncrease')}</SelectItem>
                                    <SelectItem value="manual">{t('contracts.item.sourceManual')}</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                            <div className="flex justify-end gap-2">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={cancelEditingPeriod}
                                disabled={updatingPeriod}
                              >
                                {t('common.cancel')}
                              </Button>
                              <Button
                                type="button"
                                size="sm"
                                onClick={handleUpdatePricePeriod}
                                disabled={updatingPeriod || !editPeriodFrom || !editPeriodPrice}
                              >
                                {updatingPeriod ? <Loader2 className="h-4 w-4 animate-spin" /> : t('common.save')}
                              </Button>
                            </div>
                          </div>
                        ) : (
                          /* View Mode */
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                              <span>{formatMonthYear(period.validFrom)}</span>
                              <span className="text-gray-400">→</span>
                              <span>{period.validTo ? formatMonthYear(period.validTo) : t('contracts.item.ongoing')}</span>
                              <span className="font-medium">{formatCurrencyLocal(period.unitPrice)}</span>
                              <span className="text-xs text-blue-600">/{t(`contracts.item.pricePeriodValues.${period.pricePeriod}`)}</span>
                              <span className="text-xs text-gray-500">{t(`contracts.item.source${period.source.charAt(0).toUpperCase() + period.source.slice(1)}`)}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={() => startEditingPeriod(period)}
                                className="text-gray-400 hover:text-blue-600"
                                title={t('common.edit')}
                              >
                                <Edit className="h-4 w-4" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleRemovePricePeriod(period.id)}
                                disabled={removingPeriod}
                                className="text-gray-400 hover:text-red-600"
                                title={t('common.delete')}
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 text-center py-2">{t('contracts.item.noPricePeriods')}</p>
                )}

                {/* Add New Price Period */}
                <div className="grid grid-cols-5 gap-2 pt-2 border-t">
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
                      value={newPeriodPrice}
                      onChange={(e) => setNewPeriodPrice(e.target.value)}
                      className="h-8 text-sm"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">{t('contracts.item.pricePeriod')}</label>
                    <Select value={newPeriodPricePeriod} onValueChange={setNewPeriodPricePeriod}>
                      <SelectTrigger className="h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="monthly">{t('contracts.item.pricePeriodValues.monthly')}</SelectItem>
                        <SelectItem value="bi_monthly">{t('contracts.item.pricePeriodValues.bi_monthly')}</SelectItem>
                        <SelectItem value="quarterly">{t('contracts.item.pricePeriodValues.quarterly')}</SelectItem>
                        <SelectItem value="semi_annual">{t('contracts.item.pricePeriodValues.semi_annual')}</SelectItem>
                        <SelectItem value="annual">{t('contracts.item.pricePeriodValues.annual')}</SelectItem>
                        <SelectItem value="biennial">{t('contracts.item.pricePeriodValues.biennial')}</SelectItem>
                        <SelectItem value="triennial">{t('contracts.item.pricePeriodValues.triennial')}</SelectItem>
                        <SelectItem value="quadrennial">{t('contracts.item.pricePeriodValues.quadrennial')}</SelectItem>
                        <SelectItem value="quinquennial">{t('contracts.item.pricePeriodValues.quinquennial')}</SelectItem>
                      </SelectContent>
                    </Select>
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

          {/* Order Confirmation Number */}
          <div className="space-y-2">
            <label className="text-sm font-medium">{t('contracts.item.orderConfirmationNumber')}</label>
            <Input
              placeholder={t('contracts.item.orderConfirmationNumberPlaceholder')}
              value={orderConfirmationNumber}
              onChange={(e) => setOrderConfirmationNumber(e.target.value)}
            />
          </div>

          {/* Start Date + Billing Start Date - 2 columns */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('contracts.item.startDate')}{' '}
                <span className="text-muted-foreground font-normal">{t('contracts.item.startDateSubtitle')}</span>
              </label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t('contracts.item.billingStartDate')}{' '}
                <span className="text-muted-foreground font-normal">{t('contracts.item.billingStartDateSubtitle')}</span>
              </label>
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
  const [includeAllHistory, setIncludeAllHistory] = useState(false)

  const { data, loading, error } = useQuery(BILLING_SCHEDULE_QUERY, {
    variables: {
      contractId,
      months: parseInt(months),
      includeAllHistory,
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
            id="includeAllHistory"
            checked={includeAllHistory}
            onChange={(e) => setIncludeAllHistory(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300"
          />
          <label htmlFor="includeAllHistory" className="text-sm">
            {t('contracts.forecast.includeAllHistory')}
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
              <tbody className="divide-y divide-gray-200">
                {schedule.events.map((event, eventIndex) => {
                  const eventDate = new Date(event.date)
                  const today = new Date()
                  today.setHours(0, 0, 0, 0)
                  const isFuture = eventDate >= today

                  return (
                  <tr key={eventIndex} className={isFuture ? 'bg-green-50' : 'bg-white'}>
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
                  )
                })}
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

function AttachmentsTab({
  contractId,
  attachments,
  links,
  canEdit,
  onRefetch,
}: {
  contractId: string
  attachments: Attachment[]
  links: ContractLink[]
  canEdit: boolean
  onRefetch: () => void
}) {
  const { t } = useTranslation()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAddLink, setShowAddLink] = useState(false)
  const [linkName, setLinkName] = useState('')
  const [linkUrl, setLinkUrl] = useState('')
  const [addingLink, setAddingLink] = useState(false)

  const [analyzingAttachmentId, setAnalyzingAttachmentId] = useState<string | null>(null)

  const [uploadAttachment] = useMutation(UPLOAD_ATTACHMENT_MUTATION)
  const [deleteAttachment] = useMutation(DELETE_ATTACHMENT_MUTATION)
  const [addLink] = useMutation(ADD_CONTRACT_LINK_MUTATION)
  const [deleteLink] = useMutation(DELETE_CONTRACT_LINK_MUTATION)

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) return <Image className="h-5 w-5" />
    if (contentType === 'application/pdf') return <FileText className="h-5 w-5" />
    return <File className="h-5 w-5" />
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setError(null)
    setUploading(true)

    const reader = new FileReader()
    reader.onload = async (e) => {
      const base64 = (e.target?.result as string)?.split(',')[1]
      if (!base64) {
        setError(t('attachments.readError'))
        setUploading(false)
        return
      }

      try {
        const result = await uploadAttachment({
          variables: {
            input: {
              contractId,
              fileContent: base64,
              filename: file.name,
              contentType: file.type || 'application/octet-stream',
              description: '',
            },
          },
        })

        if (result.data?.uploadContractAttachment?.success) {
          onRefetch()
        } else {
          setError(result.data?.uploadContractAttachment?.error || t('attachments.uploadFailed'))
        }
      } catch (err) {
        setError(t('attachments.uploadFailed'))
      } finally {
        setUploading(false)
      }
    }
    reader.readAsDataURL(file)

    // Reset input
    event.target.value = ''
  }

  const handleDelete = async (attachment: Attachment) => {
    if (!confirm(t('attachments.confirmDelete', { filename: attachment.originalFilename }))) {
      return
    }

    try {
      const result = await deleteAttachment({
        variables: { attachmentId: attachment.id },
      })

      if (result.data?.deleteContractAttachment?.success) {
        onRefetch()
      }
    } catch (err) {
      console.error('Failed to delete attachment:', err)
    }
  }

  const fetchWithAuth = async (url: string): Promise<Blob | null> => {
    const token = getToken()
    try {
      const response = await fetch(url, {
        headers: {
          Authorization: token ? `Bearer ${token}` : '',
        },
      })
      if (!response.ok) {
        console.error('Failed to fetch file:', response.statusText)
        return null
      }
      return await response.blob()
    } catch (err) {
      console.error('Failed to fetch file:', err)
      return null
    }
  }

  const handleDownload = async (attachment: Attachment) => {
    const blob = await fetchWithAuth(attachment.downloadUrl)
    if (!blob) return

    // Create download link
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = attachment.originalFilename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const isPreviewable = (contentType: string) => {
    // Files that can be previewed in browser
    return (
      contentType.startsWith('image/') ||
      contentType === 'application/pdf' ||
      contentType.startsWith('text/')
    )
  }

  const handlePreview = async (attachment: Attachment) => {
    const blob = await fetchWithAuth(attachment.downloadUrl)
    if (!blob) return

    // Create blob URL with correct content type and open in new tab
    const blobWithType = new Blob([blob], { type: attachment.contentType })
    const url = URL.createObjectURL(blobWithType)
    window.open(url, '_blank')
  }

  const handleAddLink = async () => {
    if (!linkName.trim() || !linkUrl.trim()) return

    // Basic URL validation
    try {
      new URL(linkUrl)
    } catch {
      setError(t('links.invalidUrl'))
      return
    }

    setAddingLink(true)
    setError(null)

    try {
      const result = await addLink({
        variables: {
          input: {
            contractId,
            name: linkName.trim(),
            url: linkUrl.trim(),
          },
        },
      })

      if (result.data?.addContractLink?.success) {
        setLinkName('')
        setLinkUrl('')
        setShowAddLink(false)
        onRefetch()
      } else {
        setError(result.data?.addContractLink?.error || t('links.addFailed'))
      }
    } catch (err) {
      setError(t('links.addFailed'))
    } finally {
      setAddingLink(false)
    }
  }

  const handleDeleteLink = async (link: ContractLink) => {
    if (!confirm(t('links.confirmDelete', { name: link.name }))) {
      return
    }

    try {
      const result = await deleteLink({
        variables: { linkId: link.id },
      })

      if (result.data?.deleteContractLink?.success) {
        onRefetch()
      }
    } catch (err) {
      console.error('Failed to delete link:', err)
    }
  }

  return (
    <div>
      {/* Upload Button */}
      {canEdit && (
        <div className="mb-4 flex justify-end">
          <label className="cursor-pointer">
            <span className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              {uploading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('attachments.uploading')}
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  {t('attachments.uploadFile')}
                </>
              )}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileSelect}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Attachments List */}
      {attachments.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <Paperclip className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-600">{t('attachments.noAttachments')}</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('attachments.filename')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('attachments.size')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('attachments.uploadedBy')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('attachments.uploadedAt')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {/* Actions */}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {attachments.map((attachment) => (
                <tr key={attachment.id}>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {getFileIcon(attachment.contentType)}
                      <span className="font-medium text-gray-900">
                        {attachment.originalFilename}
                      </span>
                    </div>
                    {attachment.description && (
                      <p className="mt-1 text-xs text-gray-500">{attachment.description}</p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-500">
                    {formatFileSize(attachment.fileSize)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {attachment.uploadedByName || '-'}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                    {formatDateTime(attachment.uploadedAt)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right">
                    {attachment.contentType === 'application/pdf' && (
                      <button
                        onClick={() => setAnalyzingAttachmentId(attachment.id)}
                        className="mr-2 text-gray-400 hover:text-purple-600"
                        title={t('pdfAnalysis.analyzeButton')}
                        data-testid={`analyze-attachment-${attachment.id}`}
                      >
                        <Scan className="h-4 w-4" />
                      </button>
                    )}
                    {isPreviewable(attachment.contentType) && (
                      <button
                        onClick={() => handlePreview(attachment)}
                        className="mr-2 text-gray-400 hover:text-blue-600"
                        title={t('attachments.preview')}
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDownload(attachment)}
                      className="mr-2 text-gray-400 hover:text-blue-600"
                      title={t('attachments.download')}
                    >
                      <Download className="h-4 w-4" />
                    </button>
                    {canEdit && (
                      <button
                        onClick={() => handleDelete(attachment)}
                        className="text-gray-400 hover:text-red-600"
                        title={t('attachments.delete')}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* PDF Analysis Panel */}
      {analyzingAttachmentId && (
        <div className="mt-6">
          <PdfAnalysisPanel
            contractId={contractId}
            attachmentId={analyzingAttachmentId}
            onClose={() => setAnalyzingAttachmentId(null)}
            onImported={() => {
              setAnalyzingAttachmentId(null)
              onRefetch()
            }}
          />
        </div>
      )}

      {/* Links Section */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Link2 className="h-5 w-5 text-gray-400" />
            <h3 className="text-lg font-semibold">{t('links.title')}</h3>
          </div>
          {canEdit && !showAddLink && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowAddLink(true)}
            >
              <Plus className="h-4 w-4 mr-1" />
              {t('links.addLink')}
            </Button>
          )}
        </div>

        {/* Add Link Form */}
        {showAddLink && (
          <div className="mb-4 rounded-lg border bg-white p-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('links.name')}</label>
                <Input
                  placeholder={t('links.namePlaceholder')}
                  value={linkName}
                  onChange={(e) => setLinkName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">{t('links.url')}</label>
                <Input
                  placeholder={t('links.urlPlaceholder')}
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setShowAddLink(false)
                  setLinkName('')
                  setLinkUrl('')
                  setError(null)
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                size="sm"
                onClick={handleAddLink}
                disabled={addingLink || !linkName.trim() || !linkUrl.trim()}
              >
                {addingLink && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {t('common.save')}
              </Button>
            </div>
          </div>
        )}

        {/* Links List */}
        {links.length === 0 ? (
          <div className="rounded-lg border bg-white p-8 text-center">
            <Link2 className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-gray-600">{t('links.noLinks')}</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('links.name')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('links.url')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('links.createdBy')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('links.createdAt')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {/* Actions */}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {links.map((link) => (
                  <tr key={link.id}>
                    <td className="px-6 py-4">
                      <span className="font-medium text-gray-900">{link.name}</span>
                    </td>
                    <td className="px-6 py-4">
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-red-600 hover:text-red-800"
                      >
                        <ExternalLink className="h-3 w-3" />
                        {link.url.length > 50 ? `${link.url.substring(0, 50)}...` : link.url}
                      </a>
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {link.createdByName || '-'}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                      {formatDateTime(link.createdAt)}
                    </td>
                    <td className="whitespace-nowrap px-6 py-4 text-right">
                      {canEdit && (
                        <button
                          onClick={() => handleDeleteLink(link)}
                          className="text-gray-400 hover:text-red-600"
                          title={t('links.delete')}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function ActivityTab({ contractId }: { contractId: number }) {
  const { t } = useTranslation()
  const { entries, totalCount, hasNextPage, loading, error, loadMore } = useAuditLogs({
    entityType: 'contract',
    entityId: contractId,
    includeRelated: true,
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
      <AuditLogTable entries={entries} showEntity={true} loading={loading && entries.length === 0} />

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
