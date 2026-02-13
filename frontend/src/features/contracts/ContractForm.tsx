import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, ArrowLeft, Check, ChevronsUpDown, Edit, ExternalLink, Trash2, Plus } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

const CUSTOMERS_SEARCH_QUERY = gql`
  query CustomersSearch($search: String) {
    customers(search: $search, page: 1, pageSize: 50, sortBy: "name", sortOrder: "asc") {
      items {
        id
        name
        address
      }
    }
  }
`

const CONTRACT_QUERY = gql`
  query Contract($id: ID!) {
    contract(id: $id) {
      id
      name
      netsuiteSalesOrderNumber
      netsuiteUrl
      poNumber
      orderConfirmationNumber
      status
      startDate
      endDate
      billingStartDate
      billingInterval
      billingAnchorDay
      billingAlignmentDate
      minDurationMonths
      noticePeriodMonths
      noticePeriodAfterMinMonths
      noticePeriodAnchor
      group {
        id
        name
      }
      customer {
        id
        name
      }
    }
  }
`

const CREATE_CONTRACT_MUTATION = gql`
  mutation CreateContract($input: CreateContractInput!) {
    createContract(input: $input) {
      success
      error
      contract {
        id
      }
    }
  }
`

const UPDATE_CONTRACT_MUTATION = gql`
  mutation UpdateContract($input: UpdateContractInput!) {
    updateContract(input: $input) {
      success
      error
      contract {
        id
        status
      }
    }
  }
`

const TRANSITION_CONTRACT_STATUS_MUTATION = gql`
  mutation TransitionContractStatus($contractId: ID!, $newStatus: String!) {
    transitionContractStatus(contractId: $contractId, newStatus: $newStatus) {
      success
      error
      contract {
        id
        status
      }
    }
  }
`

const DELETE_CONTRACT_MUTATION = gql`
  mutation DeleteContract($contractId: ID!) {
    deleteContract(contractId: $contractId) {
      success
      error
      contract {
        id
        status
      }
    }
  }
`

const CONTRACT_GROUPS_QUERY = gql`
  query ContractGroups($customerId: ID!) {
    contractGroups(customerId: $customerId) {
      id
      name
      contractCount
    }
  }
`

const CREATE_CONTRACT_GROUP_MUTATION = gql`
  mutation CreateContractGroup($customerId: ID!, $name: String!) {
    createContractGroup(customerId: $customerId, name: $name) {
      success
      error
      group {
        id
        name
        contractCount
      }
    }
  }
`

interface ContractGroup {
  id: string
  name: string
  contractCount: number
}

interface CustomerAddress {
  city?: string | null
}

interface Customer {
  id: string
  name: string
  address?: CustomerAddress | null
}

interface Contract {
  id: string
  name: string
  netsuiteSalesOrderNumber: string | null
  netsuiteUrl: string | null
  poNumber: string | null
  orderConfirmationNumber: string | null
  status: string
  startDate: string
  endDate: string | null
  billingStartDate: string
  billingInterval: string
  billingAnchorDay: number
  billingAlignmentDate: string | null
  minDurationMonths: number | null
  noticePeriodMonths: number
  noticePeriodAfterMinMonths: number | null
  noticePeriodAnchor: string
  group: { id: string; name: string } | null
  customer: Customer
}

const formSchema = z.object({
  customerId: z.string().min(1, 'Customer is required'),
  name: z.string().optional(),
  salesOrderNumber: z.string().optional().nullable(),
  netsuiteUrl: z.string().optional().nullable(),
  poNumber: z.string().optional().nullable(),
  orderConfirmationNumber: z.string().optional().nullable(),
  groupId: z.string().optional().nullable(),
  startDate: z.string().min(1, 'Start date is required'),
  endDate: z.string().optional(),
  billingStartDate: z.string().optional(),
  billingInterval: z.string(),
  billingAnchorDay: z.number().min(1).max(28),
  billingAlignmentDate: z.string().optional().nullable(),
  minDurationMonths: z.number().optional().nullable(),
  noticePeriodMonths: z.number().min(0),
  noticePeriodAfterMinMonths: z.number().optional().nullable(),
  noticePeriodAnchor: z.string(),
})

type FormData = z.infer<typeof formSchema>

const BILLING_INTERVALS = ['monthly', 'quarterly', 'semi_annual', 'annual', 'biennial', 'triennial', 'quadrennial', 'quinquennial'] as const
const NOTICE_PERIOD_ANCHORS = ['end_of_duration', 'end_of_month', 'end_of_quarter'] as const

// Status transition types
type StatusTransition = {
  from: string
  to: string
  label: string
  confirmKey: string
  isReversible: boolean
}

const STATUS_TRANSITIONS: StatusTransition[] = [
  { from: 'draft', to: 'active', label: 'activate', confirmKey: 'confirmActivate', isReversible: false },
  { from: 'active', to: 'paused', label: 'pause', confirmKey: 'confirmPause', isReversible: true },
  { from: 'active', to: 'cancelled', label: 'cancel', confirmKey: 'confirmCancel', isReversible: false },
  { from: 'paused', to: 'active', label: 'resume', confirmKey: 'confirmResume', isReversible: true },
  { from: 'paused', to: 'cancelled', label: 'cancel', confirmKey: 'confirmCancel', isReversible: false },
  { from: 'cancelled', to: 'ended', label: 'end', confirmKey: 'confirmEnd', isReversible: false },
]

const getStatusBadgeClass = (status: string) => {
  switch (status) {
    case 'active':
      return 'bg-green-100 text-green-800'
    case 'draft':
      return 'bg-gray-100 text-gray-800'
    case 'paused':
      return 'bg-yellow-100 text-yellow-800'
    case 'cancelled':
      return 'bg-red-100 text-red-800'
    case 'ended':
      return 'bg-gray-100 text-gray-600'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

export function ContractForm() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const isEdit = Boolean(id)

  const [customerSearchOpen, setCustomerSearchOpen] = useState(false)
  const [customerSearchTerm, setCustomerSearchTerm] = useState('')
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(!isEdit) // New contracts start in edit mode
  const [statusTransition, setStatusTransition] = useState<StatusTransition | null>(null)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [groupPopoverOpen, setGroupPopoverOpen] = useState(false)
  const [groupSearchTerm, setGroupSearchTerm] = useState('')
  const billingStartManuallyChanged = useRef(false)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      customerId: '',
      name: '',
      salesOrderNumber: '',
      netsuiteUrl: '',
      poNumber: '',
      orderConfirmationNumber: '',
      groupId: null,
      startDate: '',
      endDate: '',
      billingStartDate: '',
      billingInterval: 'monthly',
      billingAnchorDay: 1,
      billingAlignmentDate: '',
      minDurationMonths: null,
      noticePeriodMonths: 3,
      noticePeriodAfterMinMonths: null,
      noticePeriodAnchor: 'end_of_duration',
    },
  })

  // Search customers
  const { data: customersData, loading: loadingCustomers } = useQuery(CUSTOMERS_SEARCH_QUERY, {
    variables: { search: customerSearchTerm || null },
    skip: !customerSearchOpen && !customerSearchTerm,
  })

  // Fetch existing contract if editing
  const { data: contractData, loading: loadingContract } = useQuery(CONTRACT_QUERY, {
    variables: { id },
    skip: !isEdit,
  })

  // Fetch groups for selected customer
  const watchedCustomerId = form.watch('customerId')
  const { data: groupsData, refetch: refetchGroups } = useQuery(CONTRACT_GROUPS_QUERY, {
    variables: { customerId: watchedCustomerId },
    skip: !watchedCustomerId,
  })
  const contractGroups: ContractGroup[] = groupsData?.contractGroups || []

  const [createContract, { loading: creating }] = useMutation(CREATE_CONTRACT_MUTATION)
  const [updateContract, { loading: updating }] = useMutation(UPDATE_CONTRACT_MUTATION)
  const [deleteContract, { loading: deleting }] = useMutation(DELETE_CONTRACT_MUTATION)
  const [createContractGroup] = useMutation(CREATE_CONTRACT_GROUP_MUTATION)

  // Populate form when editing
  useEffect(() => {
    if (contractData?.contract) {
      const c = contractData.contract as Contract
      setSelectedCustomer(c.customer)
      form.reset({
        customerId: c.customer.id,
        name: c.name || '',
        salesOrderNumber: c.netsuiteSalesOrderNumber || '',
        netsuiteUrl: c.netsuiteUrl || '',
        poNumber: c.poNumber || '',
        orderConfirmationNumber: c.orderConfirmationNumber || '',
        groupId: c.group?.id || null,
        startDate: c.startDate,
        endDate: c.endDate || '',
        billingStartDate: c.billingStartDate,
        billingInterval: c.billingInterval,
        billingAnchorDay: c.billingAnchorDay,
        billingAlignmentDate: c.billingAlignmentDate || '',
        minDurationMonths: c.minDurationMonths,
        noticePeriodMonths: c.noticePeriodMonths,
        noticePeriodAfterMinMonths: c.noticePeriodAfterMinMonths,
        noticePeriodAnchor: c.noticePeriodAnchor,
      })
    }
  }, [contractData, form])

  // For new contracts: copy startDate to billingStartDate (one-time)
  const startDate = form.watch('startDate')
  useEffect(() => {
    if (!isEdit && startDate && !billingStartManuallyChanged.current) {
      form.setValue('billingStartDate', startDate)
    }
  }, [isEdit, startDate, form])

  const onSubmit = async (data: FormData) => {
    setError(null)

    try {
      if (isEdit) {
        const result = await updateContract({
          variables: {
            input: {
              id,
              name: data.name || null,
              salesOrderNumber: data.salesOrderNumber || null,
              netsuiteUrl: data.netsuiteUrl || null,
              poNumber: data.poNumber || null,
              orderConfirmationNumber: data.orderConfirmationNumber || null,
              groupId: data.groupId || null,
              startDate: data.startDate,
              billingStartDate: data.billingStartDate || data.startDate,
              endDate: data.endDate || null,
              billingInterval: data.billingInterval,
              billingAnchorDay: data.billingAnchorDay,
              billingAlignmentDate: data.billingAlignmentDate || null,
              minDurationMonths: data.minDurationMonths,
              noticePeriodMonths: data.noticePeriodMonths,
              noticePeriodAfterMinMonths: data.noticePeriodAfterMinMonths,
              noticePeriodAnchor: data.noticePeriodAnchor,
            },
          },
        })

        if (result.data?.updateContract.success) {
          navigate(`/contracts/${id}`)
        } else {
          setError(result.data?.updateContract.error || 'Update failed')
        }
      } else {
        const result = await createContract({
          variables: {
            input: {
              customerId: data.customerId,
              name: data.name || null,
              salesOrderNumber: data.salesOrderNumber || null,
              netsuiteUrl: data.netsuiteUrl || null,
              poNumber: data.poNumber || null,
              orderConfirmationNumber: data.orderConfirmationNumber || null,
              groupId: data.groupId || null,
              startDate: data.startDate,
              endDate: data.endDate || null,
              billingStartDate: data.billingStartDate || data.startDate,
              billingInterval: data.billingInterval,
              billingAnchorDay: data.billingAnchorDay,
              billingAlignmentDate: data.billingAlignmentDate || null,
              minDurationMonths: data.minDurationMonths,
              noticePeriodMonths: data.noticePeriodMonths,
              noticePeriodAfterMinMonths: data.noticePeriodAfterMinMonths,
              noticePeriodAnchor: data.noticePeriodAnchor,
            },
          },
        })

        if (result.data?.createContract.success) {
          navigate(`/contracts/${result.data.createContract.contract.id}`)
        } else {
          setError(result.data?.createContract.error || 'Creation failed')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  const customers = customersData?.customers?.items || []
  const isLoading = loadingContract || creating || updating

  const handleDeleteContract = async () => {
    if (!id) return
    const result = await deleteContract({
      variables: { contractId: id },
    })
    if (result.data?.deleteContract?.success) {
      setShowDeleteConfirm(false)
      navigate('/contracts')
    } else {
      setError(result.data?.deleteContract?.error || 'Delete failed')
      setShowDeleteConfirm(false)
    }
  }

  if (isEdit && loadingContract) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const contract = contractData?.contract as Contract | undefined

  // Get available transitions for current status
  const availableTransitions = contract
    ? STATUS_TRANSITIONS.filter((t) => t.from === contract.status)
    : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate(isEdit ? `/contracts/${id}` : '/contracts')}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('common.back')}
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">
                {isEdit
                  ? (contract?.name || contract?.customer.name || t('contracts.detail.details'))
                  : t('contracts.newContract')}
              </h1>
              {isEdit && contract && (
                <span
                  className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${getStatusBadgeClass(
                    contract.status
                  )}`}
                >
                  {t(`contracts.status.${contract.status}`)}
                </span>
              )}
            </div>
            {isEdit && contract?.name && (
              <p className="text-sm text-muted-foreground">{contract.customer.name}</p>
            )}
          </div>
        </div>
        {isEdit && !isEditing && contract && (
          <div className="flex items-center gap-2">
            {/* Delete Button - only for non-deleted/non-ended contracts */}
            {contract.status !== 'deleted' && contract.status !== 'ended' && (
              <Button
                variant="outline"
                onClick={() => setShowDeleteConfirm(true)}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t('contracts.actions.delete')}
              </Button>
            )}
            {/* Status Transition Buttons */}
            {availableTransitions.map((transition) => (
              <Button
                key={`${transition.from}-${transition.to}`}
                variant={transition.to === 'cancelled' ? 'destructive' : transition.to === 'active' ? 'default' : 'outline'}
                onClick={() => setStatusTransition(transition)}
              >
                {t(`contracts.statusTransition.${transition.label}`)}
              </Button>
            ))}
            {/* Edit Button */}
            <Button onClick={() => setIsEditing(true)}>
              <Edit className="mr-2 h-4 w-4" />
              {t('contracts.actions.edit')}
            </Button>
          </div>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{t('contracts.detail.overview')}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2">
              {/* Customer - read-only for existing contracts */}
              {isEdit ? (
                <div className="md:col-span-2">
                  <p className="text-sm font-medium">{t('contracts.customer')}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{contract?.customer.name}</p>
                </div>
              ) : (
                <FormField
                  control={form.control}
                  name="customerId"
                  render={({ field }) => (
                    <FormItem className="md:col-span-2">
                      <FormLabel>{t('contracts.customer')} *</FormLabel>
                      <Popover open={customerSearchOpen} onOpenChange={setCustomerSearchOpen}>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              variant="outline"
                              role="combobox"
                              aria-expanded={customerSearchOpen}
                              className={cn(
                                'w-full justify-between',
                                !field.value && 'text-muted-foreground'
                              )}
                            >
                              {selectedCustomer ? (
                                <span>
                                  {selectedCustomer.name}
                                  {selectedCustomer.address?.city && (
                                    <span className="ml-2 text-muted-foreground">
                                      ({selectedCustomer.address.city})
                                    </span>
                                  )}
                                </span>
                              ) : (
                                t('contracts.form.selectCustomer')
                              )}
                              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-[400px] p-0" align="start">
                          <Command shouldFilter={false}>
                            <CommandInput
                              placeholder={t('contracts.searchPlaceholder')}
                              value={customerSearchTerm}
                              onValueChange={setCustomerSearchTerm}
                            />
                            <CommandList>
                              {loadingCustomers && (
                                <div className="flex items-center justify-center py-6">
                                  <Loader2 className="h-4 w-4 animate-spin" />
                                </div>
                              )}
                              <CommandEmpty>{t('customers.noCustomers')}</CommandEmpty>
                              <CommandGroup>
                                {customers.map((customer: Customer) => (
                                  <CommandItem
                                    key={customer.id}
                                    value={customer.id}
                                    onSelect={() => {
                                      field.onChange(customer.id)
                                      setSelectedCustomer(customer)
                                      setCustomerSearchOpen(false)
                                    }}
                                  >
                                    <Check
                                      className={cn(
                                        'mr-2 h-4 w-4',
                                        field.value === customer.id ? 'opacity-100' : 'opacity-0'
                                      )}
                                    />
                                    <div className="flex flex-col">
                                      <span>{customer.name}</span>
                                      {customer.address?.city && (
                                        <span className="text-sm text-muted-foreground">
                                          {customer.address.city}
                                        </span>
                                      )}
                                    </div>
                                  </CommandItem>
                                ))}
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Contract Name */}
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.name')}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('contracts.form.namePlaceholder')}
                        disabled={!isEditing}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Sales Order Number */}
              <FormField
                control={form.control}
                name="salesOrderNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.salesOrderNumber')}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('contracts.form.salesOrderNumberPlaceholder')}
                        disabled={!isEditing}
                        {...field}
                        value={field.value || ''}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* NetSuite URL */}
              <FormField
                control={form.control}
                name="netsuiteUrl"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.netsuiteUrl')}</FormLabel>
                    {!isEditing && field.value ? (
                      <div className="flex items-center h-10">
                        <a
                          href={field.value}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-red-600 hover:text-red-800 truncate"
                        >
                          <ExternalLink className="h-3 w-3" />
                          {t('contracts.form.openInNetsuite')}
                        </a>
                      </div>
                    ) : (
                      <FormControl>
                        <Input
                          placeholder={t('contracts.form.netsuiteUrlPlaceholder')}
                          disabled={!isEditing}
                          {...field}
                          value={field.value || ''}
                        />
                      </FormControl>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* PO Number */}
              <FormField
                control={form.control}
                name="poNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.poNumber')}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('contracts.form.poNumberPlaceholder')}
                        disabled={!isEditing}
                        {...field}
                        value={field.value || ''}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Order Confirmation Number */}
              <FormField
                control={form.control}
                name="orderConfirmationNumber"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.orderConfirmationNumber')}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={t('contracts.form.orderConfirmationNumberPlaceholder')}
                        disabled={!isEditing}
                        {...field}
                        value={field.value || ''}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Group */}
              {watchedCustomerId && (
                <FormField
                  control={form.control}
                  name="groupId"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('contracts.form.group')}</FormLabel>
                      <Popover open={groupPopoverOpen} onOpenChange={setGroupPopoverOpen}>
                        <PopoverTrigger asChild>
                          <FormControl>
                            <Button
                              variant="outline"
                              role="combobox"
                              disabled={!isEditing}
                              className={cn(
                                'w-full justify-between',
                                !field.value && 'text-muted-foreground'
                              )}
                            >
                              {field.value
                                ? contractGroups.find((g) => g.id === field.value)?.name || t('contracts.form.selectGroup')
                                : t('contracts.form.noGroup')}
                              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                          </FormControl>
                        </PopoverTrigger>
                        <PopoverContent className="w-[300px] p-0" align="start">
                          <Command shouldFilter={false}>
                            <CommandInput
                              placeholder={t('contracts.form.selectGroup')}
                              value={groupSearchTerm}
                              onValueChange={setGroupSearchTerm}
                            />
                            <CommandList>
                              <CommandEmpty>
                                {groupSearchTerm.trim() ? (
                                  <button
                                    type="button"
                                    className="flex w-full items-center gap-2 px-2 py-1.5 text-sm cursor-pointer hover:bg-accent rounded"
                                    onClick={async () => {
                                      const result = await createContractGroup({
                                        variables: {
                                          customerId: watchedCustomerId,
                                          name: groupSearchTerm.trim(),
                                        },
                                      })
                                      if (result.data?.createContractGroup?.success) {
                                        const newGroup = result.data.createContractGroup.group
                                        field.onChange(newGroup.id)
                                        setGroupSearchTerm('')
                                        setGroupPopoverOpen(false)
                                        refetchGroups()
                                      }
                                    }}
                                  >
                                    <Plus className="h-4 w-4" />
                                    {t('contracts.group.createNew')}: &quot;{groupSearchTerm.trim()}&quot;
                                  </button>
                                ) : (
                                  t('contracts.group.noGroup')
                                )}
                              </CommandEmpty>
                              <CommandGroup>
                                <CommandItem
                                  value="__none__"
                                  onSelect={() => {
                                    field.onChange(null)
                                    setGroupPopoverOpen(false)
                                    setGroupSearchTerm('')
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      'mr-2 h-4 w-4',
                                      !field.value ? 'opacity-100' : 'opacity-0'
                                    )}
                                  />
                                  {t('contracts.form.noGroup')}
                                </CommandItem>
                                {contractGroups
                                  .filter((g) =>
                                    !groupSearchTerm || g.name.toLowerCase().includes(groupSearchTerm.toLowerCase())
                                  )
                                  .map((group) => (
                                    <CommandItem
                                      key={group.id}
                                      value={group.id}
                                      onSelect={() => {
                                        field.onChange(group.id)
                                        setGroupPopoverOpen(false)
                                        setGroupSearchTerm('')
                                      }}
                                    >
                                      <Check
                                        className={cn(
                                          'mr-2 h-4 w-4',
                                          field.value === group.id ? 'opacity-100' : 'opacity-0'
                                        )}
                                      />
                                      {group.name}
                                    </CommandItem>
                                  ))}
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Start Date */}
              <FormField
                control={form.control}
                name="startDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.startDate')} *</FormLabel>
                    <FormControl>
                      <Input
                        type="date"
                        {...field}
                        disabled={!isEditing}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* End Date */}
              <FormField
                control={form.control}
                name="endDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.endDate')}</FormLabel>
                    <div className="flex gap-2">
                      <FormControl>
                        <Input type="date" {...field} disabled={!isEditing} />
                      </FormControl>
                      {isEditing && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => field.onChange('')}
                          className="shrink-0"
                        >
                          {t('contracts.form.indefinite')}
                        </Button>
                      )}
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('contracts.form.billingInterval')}</CardTitle>
              <p className="text-sm text-muted-foreground">{t('contracts.form.billingDescription')}</p>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              {/* Billing Start Date */}
              <FormField
                control={form.control}
                name="billingStartDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.billingStartDate')}</FormLabel>
                    <FormControl>
                      <Input
                        type="date"
                        {...field}
                        disabled={!isEditing}
                        onChange={(e) => {
                          billingStartManuallyChanged.current = true
                          field.onChange(e)
                        }}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Billing Interval */}
              <FormField
                control={form.control}
                name="billingInterval"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.billingInterval')}</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={!isEditing}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {BILLING_INTERVALS.map((interval) => (
                          <SelectItem key={interval} value={interval}>
                            {t(`contracts.billingInterval.${interval}`)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Billing Anchor Day - only for monthly/quarterly */}
              {(form.watch('billingInterval') === 'monthly' ||
                form.watch('billingInterval') === 'quarterly') && (
                <FormField
                  control={form.control}
                  name="billingAnchorDay"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('contracts.form.billingAnchorDay')}</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={1}
                          max={28}
                          disabled={!isEditing}
                          {...field}
                          onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Billing Alignment Date - only for intervals larger than monthly */}
              {form.watch('billingInterval') !== 'monthly' && (
                <FormField
                  control={form.control}
                  name="billingAlignmentDate"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('contracts.form.billingAlignmentDate')}</FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          {...field}
                          value={field.value || ''}
                          disabled={!isEditing}
                        />
                      </FormControl>
                      <p className="text-xs text-muted-foreground">
                        {t('contracts.form.billingAlignmentDateHint')}
                      </p>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('contracts.form.noticePeriod')}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              {/* Min Duration */}
              <FormField
                control={form.control}
                name="minDurationMonths"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.minDuration')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        disabled={!isEditing}
                        {...field}
                        value={field.value ?? ''}
                        onChange={(e) =>
                          field.onChange(e.target.value ? parseInt(e.target.value) : null)
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Notice Period */}
              <FormField
                control={form.control}
                name="noticePeriodMonths"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.noticePeriod')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        disabled={!isEditing}
                        {...field}
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 0)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Notice Period After Minimum Duration */}
              <FormField
                control={form.control}
                name="noticePeriodAfterMinMonths"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.noticePeriodAfterMin')}</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        placeholder={t('contracts.form.noticePeriodAfterMinHint')}
                        disabled={!isEditing}
                        {...field}
                        value={field.value ?? ''}
                        onChange={(e) =>
                          field.onChange(e.target.value ? parseInt(e.target.value) : null)
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Notice Period Anchor */}
              <FormField
                control={form.control}
                name="noticePeriodAnchor"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t('contracts.form.noticePeriodAnchor')}</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value} disabled={!isEditing}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {NOTICE_PERIOD_ANCHORS.map((anchor) => (
                          <SelectItem key={anchor} value={anchor}>
                            {t(`contracts.noticePeriodAnchor.${anchor}`)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {isEditing && (
            <div className="flex justify-end gap-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (isEdit) {
                    setIsEditing(false)
                    // Reset form to original values
                    if (contract) {
                      form.reset({
                        customerId: contract.customer.id,
                        name: contract.name || '',
                        salesOrderNumber: contract.netsuiteSalesOrderNumber || '',
                        netsuiteUrl: contract.netsuiteUrl || '',
                        poNumber: contract.poNumber || '',
                        orderConfirmationNumber: contract.orderConfirmationNumber || '',
                        groupId: contract.group?.id || null,
                        startDate: contract.startDate,
                        endDate: contract.endDate || '',
                        billingStartDate: contract.billingStartDate,
                        billingInterval: contract.billingInterval,
                        billingAnchorDay: contract.billingAnchorDay,
                        billingAlignmentDate: contract.billingAlignmentDate || '',
                        minDurationMonths: contract.minDurationMonths,
                        noticePeriodMonths: contract.noticePeriodMonths,
                        noticePeriodAfterMinMonths: contract.noticePeriodAfterMinMonths,
                        noticePeriodAnchor: contract.noticePeriodAnchor,
                      })
                    }
                  } else {
                    navigate('/contracts')
                  }
                }}
              >
                {t('contracts.actions.cancel')}
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('contracts.actions.save')}
              </Button>
            </div>
          )}
        </form>
      </Form>

      {/* Status Transition Modal */}
      {statusTransition && id && (
        <StatusTransitionModal
          contractId={id}
          transition={statusTransition}
          onClose={() => setStatusTransition(null)}
          onSuccess={() => {
            setStatusTransition(null)
            // Refetch contract data
            window.location.reload()
          }}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>{t('contracts.deleteConfirm.title')}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p>{t('contracts.deleteConfirm.message')}</p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteConfirm(false)}>
              {t('contracts.actions.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteContract}
              disabled={deleting}
            >
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('contracts.actions.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// Status Transition Modal Component
function StatusTransitionModal({
  contractId,
  transition,
  onClose,
  onSuccess,
}: {
  contractId: string
  transition: StatusTransition
  onClose: () => void
  onSuccess: () => void
}) {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)

  const [transitionStatus, { loading }] = useMutation(TRANSITION_CONTRACT_STATUS_MUTATION)

  const handleConfirm = async () => {
    setError(null)

    try {
      const result = await transitionStatus({
        variables: {
          contractId,
          newStatus: transition.to,
        },
      })

      if (result.data?.transitionContractStatus.success) {
        onSuccess()
      } else {
        setError(result.data?.transitionContractStatus.error || 'Status change failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    }
  }

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t('contracts.statusTransition.confirmTitle')}</DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <div className="space-y-4 py-4">
          <p>{t(`contracts.statusTransition.${transition.confirmKey}`)}</p>
          <p className={`text-sm ${transition.isReversible ? 'text-muted-foreground' : 'text-destructive font-medium'}`}>
            {transition.isReversible
              ? t('contracts.statusTransition.warningReversible')
              : t('contracts.statusTransition.warningIrreversible')}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('contracts.actions.cancel')}
          </Button>
          <Button
            variant={transition.to === 'cancelled' || transition.to === 'ended' ? 'destructive' : 'default'}
            onClick={handleConfirm}
            disabled={loading}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t(`contracts.statusTransition.${transition.label}`)}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
