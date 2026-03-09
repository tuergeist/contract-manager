import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useLazyQuery, useMutation, gql } from '@apollo/client'
import { Loader2, CheckCircle2, AlertCircle, Link2, Plus } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'

const PREVIEW_ACTIVATION = gql`
  query PreviewContractActivation($contractId: ID!) {
    previewContractActivation(contractId: $contractId) {
      clockodoConfigured
      customerLinked
      customerName
      customerId
      clockodoCustomerId
      maintenanceNeeded
      maintenanceProjectExists
      maintenanceProjectName
      oneOffItems {
        id
        description
      }
    }
  }
`

const PROVISION_PROJECTS = gql`
  mutation ProvisionClockodoProjects(
    $contractId: ID!
    $createMaintenance: Boolean!
    $oneoffStrategy: String!
    $selectedOneoffItemIds: [Int!]
  ) {
    provisionClockodoProjects(
      contractId: $contractId
      createMaintenance: $createMaintenance
      oneoffStrategy: $oneoffStrategy
      selectedOneoffItemIds: $selectedOneoffItemIds
    ) {
      success
      createdProjects {
        name
        action
      }
      errors
    }
  }
`

const CLOCKODO_CUSTOMERS = gql`
  query ClockodoCustomers {
    clockodoCustomers
  }
`

const CREATE_CLOCKODO_CUSTOMER = gql`
  mutation CreateClockodoCustomer($customerId: ID!) {
    createClockodoCustomer(customerId: $customerId) {
      success
      error
    }
  }
`

const LINK_CUSTOMER_TO_CLOCKODO = gql`
  mutation LinkCustomerToClockodo($customerId: ID!, $clockodoCustomerId: String!) {
    linkCustomerToClockodo(customerId: $customerId, clockodoCustomerId: $clockodoCustomerId) {
      success
      error
    }
  }
`

/** Extract the first word (split by space or dash) as a search seed, stripping legal suffixes. */
function getSearchSeed(customerName: string): string {
  return customerName.split(/[\s\-]+/)[0] || ''
}

/** Parse "id:name" strings from backend into structured objects. */
function parseClockodoCustomers(raw: string[]): { id: string; name: string }[] {
  return raw.map((c) => {
    const idx = c.indexOf(':')
    return { id: c.slice(0, idx), name: c.slice(idx + 1) }
  })
}

interface ClockodoActivationDialogProps {
  contractId: string
  open: boolean
  onClose: () => void
  onComplete: () => void
}

export function ClockodoActivationDialog({ contractId, open, onClose, onComplete }: ClockodoActivationDialogProps) {
  const { t } = useTranslation()
  const [oneoffStrategy, setOneoffStrategy] = useState<'combined' | 'per_item' | 'skip'>('combined')
  const [createMaintenance, setCreateMaintenance] = useState(true)
  const [provisioned, setProvisioned] = useState(false)
  const [results, setResults] = useState<{ name: string; action: string }[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [confirmCreate, setConfirmCreate] = useState(false)
  const [customerSearch, setCustomerSearch] = useState('')


  const { data, loading, refetch } = useQuery(PREVIEW_ACTIVATION, {
    variables: { contractId },
    skip: !open,
  })

  const [provision, { loading: provisioning }] = useMutation(PROVISION_PROJECTS)
  const [fetchClockodoCustomers, { data: clockodoData, loading: loadingClockodoCustomers }] = useLazyQuery(CLOCKODO_CUSTOMERS)
  const [createClockodoCustomer, { loading: creatingCustomer }] = useMutation(CREATE_CLOCKODO_CUSTOMER)
  const [linkCustomer, { loading: linkingCustomer }] = useMutation(LINK_CUSTOMER_TO_CLOCKODO)

  const preview = data?.previewContractActivation

  // Pre-populate search and fetch Clockodo customers when customer is not linked
  useEffect(() => {
    if (preview && !preview.customerLinked && preview.clockodoConfigured) {
      setCustomerSearch(getSearchSeed(preview.customerName))
      fetchClockodoCustomers()
    }
  }, [preview, fetchClockodoCustomers])

  const handleProvision = async () => {
    const result = await provision({
      variables: {
        contractId,
        createMaintenance,
        oneoffStrategy,
        selectedOneoffItemIds: null,
      },
    })
    const d = result.data?.provisionClockodoProjects
    if (d) {
      setResults(d.createdProjects)
      setErrors(d.errors)
      setProvisioned(true)
    }
  }

  const handleComplete = () => {
    onComplete()
  }

  const handleCreateInClockodo = async () => {
    if (!preview) return
    const result = await createClockodoCustomer({
      variables: { customerId: String(preview.customerId) },
    })
    if (result.data?.createClockodoCustomer?.success) {
      await refetch()
    }
  }

  const handleSelectAndLink = async (clockodoCustomerId: string) => {
    if (!preview) return
    const result = await linkCustomer({
      variables: {
        customerId: String(preview.customerId),
        clockodoCustomerId,
      },
    })
    if (result.data?.linkCustomerToClockodo?.success) {
      await refetch()
    }
  }

  if (loading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  if (!preview) return null

  // If Clockodo isn't configured, skip entirely
  if (!preview.clockodoConfigured) {
    onComplete()
    return null
  }

  const allClockodoCustomers = parseClockodoCustomers((clockodoData?.clockodoCustomers || []) as string[])
  const filteredCustomers = customerSearch
    ? allClockodoCustomers.filter((c) => c.name.toLowerCase().includes(customerSearch.toLowerCase()))
    : allClockodoCustomers

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('clockodo.activation.title')}</DialogTitle>
        </DialogHeader>

        {!provisioned ? (
          <div className="space-y-4">
            {/* Customer linking status */}
            <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
              {preview.customerLinked ? (
                <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-500 mt-0.5" />
              )}
              <div className="flex-1">
                <p className="text-sm font-medium">
                  {preview.customerLinked
                    ? t('clockodo.activation.customerLinked', { name: preview.customerName })
                    : t('clockodo.activation.customerNotLinked', { name: preview.customerName })
                  }
                </p>
                {!preview.customerLinked && (
                  <div className="mt-2 space-y-3">
                    <div>
                      {linkingCustomer ? (
                        <div className="flex items-center gap-2 py-2">
                          <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                          <span className="text-xs text-gray-500">{t('clockodo.activation.linkingCustomer')}</span>
                        </div>
                      ) : loadingClockodoCustomers ? (
                        <div className="flex items-center gap-2 py-2">
                          <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                        </div>
                      ) : (
                        <Command shouldFilter={false} className="rounded-md border">
                          <CommandInput
                            placeholder={t('clockodo.activation.selectClockodoCustomer')}
                            value={customerSearch}
                            onValueChange={setCustomerSearch}
                          />
                          <CommandList className="max-h-[150px]">
                            <CommandEmpty>{t('common.noResults')}</CommandEmpty>
                            <CommandGroup>
                              {filteredCustomers.map((c) => (
                                <CommandItem
                                  key={c.id}
                                  value={c.id}
                                  onSelect={() => handleSelectAndLink(c.id)}
                                >
                                  {c.name}
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </CommandList>
                        </Command>
                      )}
                    </div>
                    <div>
                      {!confirmCreate ? (
                        <button
                          onClick={() => setConfirmCreate(true)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-500 hover:text-gray-700"
                        >
                          <Plus className="h-3 w-3" />
                          {t('clockodo.activation.createInClockodo')}
                        </button>
                      ) : (
                        <button
                          onClick={handleCreateInClockodo}
                          disabled={creatingCustomer}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
                        >
                          {creatingCustomer ? <Loader2 className="h-3 w-3 animate-spin" /> : <Plus className="h-3 w-3" />}
                          {creatingCustomer ? t('clockodo.activation.creatingCustomer') : t('clockodo.activation.confirmCreate')}
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {preview.customerLinked && (
              <>
                {/* Maintenance project */}
                {preview.maintenanceNeeded && (
                  <div className="p-3 rounded-lg border space-y-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="createMaintenance"
                        checked={createMaintenance}
                        onChange={(e) => setCreateMaintenance(e.target.checked)}
                        className="rounded"
                      />
                      <label htmlFor="createMaintenance" className="text-sm font-medium">
                        {t('clockodo.activation.maintenanceProject')}
                      </label>
                    </div>
                    <p className="text-xs text-gray-500 ml-6">
                      {preview.maintenanceProjectExists ? (
                        <span className="flex items-center gap-1">
                          <Link2 className="h-3 w-3" />
                          {t('clockodo.activation.maintenanceExists', { name: preview.maintenanceProjectName })}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Plus className="h-3 w-3" />
                          {t('clockodo.activation.maintenanceCreate', { name: preview.maintenanceProjectName })}
                        </span>
                      )}
                    </p>
                  </div>
                )}

                {/* One-off items */}
                {preview.oneOffItems.length > 0 && (
                  <div className="p-3 rounded-lg border space-y-2">
                    <p className="text-sm font-medium">{t('clockodo.activation.oneOffProjects')}</p>
                    <p className="text-xs text-gray-500">
                      {preview.oneOffItems.map((i: { description: string }) => i.description).join(', ')}
                    </p>
                    <div className="space-y-1.5 mt-2">
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="radio"
                          name="oneoffStrategy"
                          checked={oneoffStrategy === 'combined'}
                          onChange={() => setOneoffStrategy('combined')}
                        />
                        {t('clockodo.activation.oneOffCombined')}
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="radio"
                          name="oneoffStrategy"
                          checked={oneoffStrategy === 'per_item'}
                          onChange={() => setOneoffStrategy('per_item')}
                        />
                        {t('clockodo.activation.oneOffPerItem')}
                      </label>
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          type="radio"
                          name="oneoffStrategy"
                          checked={oneoffStrategy === 'skip'}
                          onChange={() => setOneoffStrategy('skip')}
                        />
                        {t('clockodo.activation.oneOffSkip')}
                      </label>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span>{r.name}</span>
                <span className="text-xs text-gray-400">({r.action})</span>
              </div>
            ))}
            {errors.map((e, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                <span>{e}</span>
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          {!provisioned ? (
            <>
              <button onClick={handleComplete} className="px-4 py-2 text-sm border rounded-md hover:bg-gray-50">
                {t('clockodo.activation.skip')}
              </button>
              {preview.customerLinked && (
                <button
                  onClick={handleProvision}
                  disabled={provisioning || (!createMaintenance && oneoffStrategy === 'skip')}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {provisioning ? <Loader2 className="h-4 w-4 animate-spin" /> : t('clockodo.activation.createAndActivate')}
                </button>
              )}
            </>
          ) : (
            <button onClick={handleComplete} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
              {t('clockodo.activation.continue')}
            </button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
