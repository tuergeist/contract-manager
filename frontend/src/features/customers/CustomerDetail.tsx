import { useState, useMemo, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, ArrowLeft, Building2, MapPin, FileText, ExternalLink, ArrowUpDown, ArrowUp, ArrowDown, History, Paperclip, Upload, Download, File, Image, Trash2, Link2, Plus, TrendingUp, DollarSign, ListTodo } from 'lucide-react'
import { TodoModal, type TodoContext } from '@/features/todos'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDate } from '@/lib/utils'
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
    }
  }
`

const UPLOAD_CUSTOMER_ATTACHMENT_MUTATION = gql`
  mutation UploadCustomerAttachment($input: UploadCustomerAttachmentInput!) {
    uploadCustomerAttachment(input: $input) {
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

const DELETE_CUSTOMER_ATTACHMENT_MUTATION = gql`
  mutation DeleteCustomerAttachment($attachmentId: ID!) {
    deleteCustomerAttachment(attachmentId: $attachmentId) {
      success
      error
    }
  }
`

const ADD_CUSTOMER_LINK_MUTATION = gql`
  mutation AddCustomerLink($input: AddCustomerLinkInput!) {
    addCustomerLink(input: $input) {
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

const DELETE_CUSTOMER_LINK_MUTATION = gql`
  mutation DeleteCustomerLink($linkId: ID!) {
    deleteCustomerLink(linkId: $linkId) {
      success
      error
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

interface CustomerLink {
  id: string
  name: string
  url: string
  createdAt: string
  createdByName: string | null
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
  attachments: Attachment[]
  links: CustomerLink[]
}

interface CustomerData {
  customer: Customer | null
}

export function CustomerDetail() {
  const { id } = useParams<{ id: string }>()
  const { t, i18n } = useTranslation()
  const [sortField, setSortField] = useState<SortField>(null)
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  // Attachment state
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadingFile, setUploadingFile] = useState(false)
  const [attachmentDescription, setAttachmentDescription] = useState('')

  // Link state
  const [newLinkName, setNewLinkName] = useState('')
  const [newLinkUrl, setNewLinkUrl] = useState('')
  const [addingLink, setAddingLink] = useState(false)

  // Todo state
  const [todoModalOpen, setTodoModalOpen] = useState(false)
  const [todoContext, setTodoContext] = useState<TodoContext | undefined>()

  const { data, loading, error, refetch } = useQuery<CustomerData>(CUSTOMER_QUERY, {
    variables: { id },
    skip: !id,
  })

  // Mutations
  const [uploadAttachment] = useMutation(UPLOAD_CUSTOMER_ATTACHMENT_MUTATION)
  const [deleteAttachment] = useMutation(DELETE_CUSTOMER_ATTACHMENT_MUTATION)
  const [addLink] = useMutation(ADD_CUSTOMER_LINK_MUTATION)
  const [deleteLink] = useMutation(DELETE_CUSTOMER_LINK_MUTATION)

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

  // Calculate totals for active contracts
  const contractTotals = useMemo(() => {
    if (!customer?.contracts) return { totalValue: 0, totalArr: 0, activeCount: 0 }

    const activeContracts = customer.contracts.filter(c => c.status === 'active')
    return {
      totalValue: activeContracts.reduce((sum, c) => sum + parseFloat(c.totalValue || '0'), 0),
      totalArr: activeContracts.reduce((sum, c) => sum + parseFloat(c.arr || '0'), 0),
      activeCount: activeContracts.length,
    }
  }, [customer?.contracts])

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

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (contentType: string) => {
    if (contentType.startsWith('image/')) {
      return <Image className="h-4 w-4 text-blue-500" />
    }
    return <File className="h-4 w-4 text-gray-500" />
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !id) return

    setUploadingFile(true)
    try {
      const reader = new FileReader()
      reader.onload = async () => {
        const base64 = (reader.result as string).split(',')[1]
        const result = await uploadAttachment({
          variables: {
            input: {
              customerId: id,
              fileContent: base64,
              filename: file.name,
              contentType: file.type || 'application/octet-stream',
              description: attachmentDescription,
            },
          },
        })

        if (result.data?.uploadCustomerAttachment?.success) {
          setAttachmentDescription('')
          refetch()
        } else {
          alert(result.data?.uploadCustomerAttachment?.error || 'Upload failed')
        }
      }
      reader.readAsDataURL(file)
    } catch (err) {
      console.error('Upload error:', err)
      alert('Upload failed')
    } finally {
      setUploadingFile(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDeleteAttachment = async (attachmentId: string) => {
    if (!confirm(t('attachments.confirmDelete'))) return

    try {
      const result = await deleteAttachment({
        variables: { attachmentId },
      })

      if (result.data?.deleteCustomerAttachment?.success) {
        refetch()
      } else {
        alert(result.data?.deleteCustomerAttachment?.error || 'Delete failed')
      }
    } catch (err) {
      console.error('Delete error:', err)
      alert('Delete failed')
    }
  }

  const handleAddLink = async () => {
    if (!newLinkName.trim() || !newLinkUrl.trim() || !id) return

    setAddingLink(true)
    try {
      const result = await addLink({
        variables: {
          input: {
            customerId: id,
            name: newLinkName.trim(),
            url: newLinkUrl.trim(),
          },
        },
      })

      if (result.data?.addCustomerLink?.success) {
        setNewLinkName('')
        setNewLinkUrl('')
        refetch()
      } else {
        alert(result.data?.addCustomerLink?.error || 'Failed to add link')
      }
    } catch (err) {
      console.error('Add link error:', err)
      alert('Failed to add link')
    } finally {
      setAddingLink(false)
    }
  }

  const handleDeleteLink = async (linkId: string) => {
    if (!confirm(t('links.confirmDelete'))) return

    try {
      const result = await deleteLink({
        variables: { linkId },
      })

      if (result.data?.deleteCustomerLink?.success) {
        refetch()
      } else {
        alert(result.data?.deleteCustomerLink?.error || 'Delete failed')
      }
    } catch (err) {
      console.error('Delete link error:', err)
      alert('Delete failed')
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
        {/* Add Todo Button */}
        <Button
          variant="outline"
          onClick={() => {
            setTodoContext({
              type: 'customer',
              id: parseInt(id!),
              name: customer.name,
            })
            setTodoModalOpen(true)
          }}
        >
          <ListTodo className="mr-2 h-4 w-4" />
          {t('todos.addTodo')}
        </Button>
      </div>

      {/* Summary Cards - 4 in a row */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Contract Value Card */}
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">{t('customers.totalContractValue')}</p>
              <p className="mt-1 text-xl font-semibold text-gray-900">
                {new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(contractTotals.totalValue)}
              </p>
            </div>
            <div className="rounded-full bg-blue-100 p-2">
              <DollarSign className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {t('customers.activeContractsCount', { count: contractTotals.activeCount })}
          </p>
        </div>

        {/* Total ARR Card */}
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">{t('customers.totalArr')}</p>
              <p className="mt-1 text-xl font-semibold text-gray-900">
                {new Intl.NumberFormat(i18n.language, { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(contractTotals.totalArr)}
              </p>
            </div>
            <div className="rounded-full bg-green-100 p-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
            </div>
          </div>
          <p className="mt-1 text-xs text-gray-500">
            {t('customers.annualRecurringRevenue')}
          </p>
        </div>

        {/* Address Card */}
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="h-4 w-4 text-gray-400" />
            <p className="text-sm font-medium text-gray-500">{t('customers.address')}</p>
          </div>
          {addressParts ? (
            <div className="text-sm text-gray-900 space-y-0.5">
              {addressParts.map((part, index) => (
                <p key={index} className="truncate">{part}</p>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-400 italic">-</p>
          )}
        </div>

        {/* Info Card */}
        <div className="rounded-lg border bg-white p-4">
          <div className="flex items-center gap-2 mb-2">
            <Building2 className="h-4 w-4 text-gray-400" />
            <p className="text-sm font-medium text-gray-500">{t('customers.info')}</p>
          </div>
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-500">{t('customers.createdAt')}</span>
              <span className="text-gray-900">{formatDate(customer.createdAt)}</span>
            </div>
            {customer.syncedAt && (
              <div className="flex justify-between">
                <span className="text-gray-500">{t('customers.syncedAt')}</span>
                <span className="text-gray-900">{formatDate(customer.syncedAt)}</span>
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

      {/* Attachments Section */}
      <div className="mt-8" data-testid="customer-attachments-section">
        <div className="flex items-center gap-2 mb-4">
          <Paperclip className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold">{t('attachments.title')}</h2>
          <span className="text-sm text-gray-500">
            ({customer.attachments?.length || 0})
          </span>
        </div>

        <div className="rounded-lg border bg-white p-6">
          {/* Upload Form */}
          <div className="flex items-end gap-4 mb-6">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('attachments.description')}
              </label>
              <Input
                value={attachmentDescription}
                onChange={(e) => setAttachmentDescription(e.target.value)}
                placeholder={t('attachments.descriptionPlaceholder')}
              />
            </div>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingFile}
              >
                {uploadingFile ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                {t('attachments.upload')}
              </Button>
            </div>
          </div>

          {/* Attachments List */}
          {customer.attachments?.length > 0 ? (
            <div className="space-y-2">
              {customer.attachments.map((attachment) => (
                <div
                  key={attachment.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-gray-50 hover:bg-gray-100"
                >
                  <div className="flex items-center gap-3">
                    {getFileIcon(attachment.contentType)}
                    <div>
                      <p className="font-medium text-sm">{attachment.originalFilename}</p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(attachment.fileSize)}
                        {attachment.description && ` • ${attachment.description}`}
                        {attachment.uploadedByName && ` • ${attachment.uploadedByName}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <a
                      href={attachment.downloadUrl}
                      className="p-2 text-gray-500 hover:text-blue-600"
                      title={t('attachments.download')}
                    >
                      <Download className="h-4 w-4" />
                    </a>
                    <button
                      onClick={() => handleDeleteAttachment(attachment.id)}
                      className="p-2 text-gray-500 hover:text-red-600"
                      title={t('attachments.delete')}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">
              {t('attachments.noAttachments')}
            </p>
          )}
        </div>
      </div>

      {/* Links Section */}
      <div className="mt-8" data-testid="customer-links-section">
        <div className="flex items-center gap-2 mb-4">
          <Link2 className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold">{t('links.title')}</h2>
          <span className="text-sm text-gray-500">
            ({customer.links?.length || 0})
          </span>
        </div>

        <div className="rounded-lg border bg-white p-6">
          {/* Add Link Form */}
          <div className="flex items-end gap-4 mb-6">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('links.name')}
              </label>
              <Input
                value={newLinkName}
                onChange={(e) => setNewLinkName(e.target.value)}
                placeholder={t('links.namePlaceholder')}
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('links.url')}
              </label>
              <Input
                value={newLinkUrl}
                onChange={(e) => setNewLinkUrl(e.target.value)}
                placeholder="https://..."
              />
            </div>
            <Button
              onClick={handleAddLink}
              disabled={addingLink || !newLinkName.trim() || !newLinkUrl.trim()}
            >
              {addingLink ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Plus className="h-4 w-4 mr-2" />
              )}
              {t('links.add')}
            </Button>
          </div>

          {/* Links List */}
          {customer.links?.length > 0 ? (
            <div className="space-y-2">
              {customer.links.map((link) => (
                <div
                  key={link.id}
                  className="flex items-center justify-between p-3 rounded-lg border bg-gray-50 hover:bg-gray-100"
                >
                  <div className="flex items-center gap-3">
                    <Link2 className="h-4 w-4 text-blue-500" />
                    <div>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-sm text-blue-600 hover:text-blue-800 hover:underline"
                      >
                        {link.name}
                      </a>
                      <p className="text-xs text-gray-500">
                        {link.url}
                        {link.createdByName && ` • ${link.createdByName}`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteLink(link.id)}
                    className="p-2 text-gray-500 hover:text-red-600"
                    title={t('links.delete')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 text-center py-4">
              {t('links.noLinks')}
            </p>
          )}
        </div>
      </div>

      {/* Activity Section */}
      <div className="mt-8" data-testid="customer-activity-section">
        <div className="flex items-center gap-2 mb-4">
          <History className="h-5 w-5 text-gray-400" />
          <h2 className="text-lg font-semibold">{t('audit.activity')}</h2>
        </div>
        <CustomerActivityLog customerId={parseInt(id!, 10)} />
      </div>

      {/* Todo Modal */}
      <TodoModal
        open={todoModalOpen}
        onOpenChange={setTodoModalOpen}
        context={todoContext}
      />
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
