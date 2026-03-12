import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Check, ChevronsUpDown, AlertTriangle, GitMerge } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
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

const MERGE_PREVIEW_QUERY = gql`
  query MergeContractPreview($sourceId: ID!, $targetId: ID!) {
    mergeContractPreview(sourceContractId: $sourceId, targetContractId: $targetId) {
      items {
        id
        productName
        description
        quantity
        unitPrice
        pricePeriod
        startDate
        billingStartDate
        isOneOff
      }
      willCreateAmendments
      sourceContractName
      targetContractName
      clockodoPreview {
        hasNewRecurringItems
        newOneOffItems
        sourceMappingsWillBeDeleted
      }
      errors
    }
  }
`

const MERGE_CONTRACT_MUTATION = gql`
  mutation MergeContract($input: MergeContractInput!) {
    mergeContract(input: $input) {
      success
      errors
      itemsTransferred
      contract {
        id
        name
      }
    }
  }
`

const TARGET_CONTRACTS_QUERY = gql`
  query Contracts($search: String, $status: String, $page: Int, $pageSize: Int) {
    contracts(search: $search, status: $status, page: $page, pageSize: $pageSize) {
      items {
        id
        name
        status
        customer {
          id
          name
        }
      }
    }
  }
`

interface MergeContractDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contractId: string
  contractName: string
  customerId: string
  customerName: string
}

interface PreviewItem {
  id: number
  productName: string | null
  description: string
  quantity: number
  unitPrice: string
  pricePeriod: string
  startDate: string | null
  billingStartDate: string | null
  isOneOff: boolean
}

interface ItemOverride {
  itemId: number
  startDate?: string
  billingStartDate?: string
}

export function MergeContractDialog({
  open,
  onOpenChange,
  contractId,
  contractName,
  customerId,
  customerName,
}: MergeContractDialogProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const [targetContractId, setTargetContractId] = useState<string | null>(null)
  const [contractSearchOpen, setContractSearchOpen] = useState(false)
  const [contractSearchTerm, setContractSearchTerm] = useState('')
  const [itemOverrides, setItemOverrides] = useState<Record<number, { startDate?: string; billingStartDate?: string }>>({})
  const [error, setError] = useState<string | null>(null)

  // Query eligible target contracts (same customer, not deleted/cancelled/ended)
  const { data: contractsData, loading: loadingContracts } = useQuery(TARGET_CONTRACTS_QUERY, {
    variables: { search: contractSearchTerm || customerName, pageSize: 50 },
    skip: !open,
  })

  // Filter to same customer and exclude source + non-mergeable statuses
  const eligibleContracts = (contractsData?.contracts?.items || []).filter(
    (c: { id: string; status: string; customer: { id: string } }) =>
      c.customer.id === customerId &&
      c.id !== contractId &&
      !['deleted', 'cancelled', 'ended'].includes(c.status)
  )

  const selectedContract = eligibleContracts.find((c: { id: string }) => c.id === targetContractId)

  // Preview query - only runs when target is selected
  const { data: previewData, loading: loadingPreview } = useQuery(MERGE_PREVIEW_QUERY, {
    variables: { sourceId: contractId, targetId: targetContractId },
    skip: !targetContractId,
  })

  const preview = previewData?.mergeContractPreview
  const previewItems: PreviewItem[] = preview?.items || []

  const [mergeContract, { loading: merging }] = useMutation(MERGE_CONTRACT_MUTATION)

  const handleMerge = async () => {
    if (!targetContractId) return
    setError(null)

    const overrides: ItemOverride[] = Object.entries(itemOverrides)
      .filter(([, v]) => v.startDate || v.billingStartDate)
      .map(([itemId, v]) => ({
        itemId: parseInt(itemId),
        ...(v.startDate ? { startDate: v.startDate } : {}),
        ...(v.billingStartDate ? { billingStartDate: v.billingStartDate } : {}),
      }))

    try {
      const result = await mergeContract({
        variables: {
          input: {
            sourceContractId: contractId,
            targetContractId,
            ...(overrides.length > 0 ? { itemOverrides: overrides } : {}),
          },
        },
      })

      const data = result.data?.mergeContract
      if (data?.success) {
        onOpenChange(false)
        navigate(`/contracts/${data.contract.id}`)
      } else {
        setError(data?.errors?.join('; ') || t('contracts.merge.errorGeneric'))
      }
    } catch (e) {
      setError(String(e))
    }
  }

  const updateOverride = (itemId: number, field: 'startDate' | 'billingStartDate', value: string) => {
    setItemOverrides((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], [field]: value || undefined },
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <GitMerge className="h-5 w-5" />
            {t('contracts.merge.title')}
          </DialogTitle>
          <DialogDescription>
            {t('contracts.merge.description', { name: contractName })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Target Contract Selector */}
          <div className="space-y-2">
            <Label>{t('contracts.merge.targetLabel')}</Label>
            <Popover open={contractSearchOpen} onOpenChange={setContractSearchOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={contractSearchOpen}
                  className="w-full justify-between"
                  data-testid="merge-target-selector"
                >
                  {selectedContract
                    ? `${selectedContract.name || t('contracts.merge.untitled')} (${selectedContract.status})`
                    : t('contracts.merge.selectTarget')}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder={t('contracts.merge.searchPlaceholder')}
                    value={contractSearchTerm}
                    onValueChange={setContractSearchTerm}
                  />
                  <CommandList>
                    {loadingContracts && (
                      <div className="flex items-center justify-center py-6">
                        <Loader2 className="h-4 w-4 animate-spin" />
                      </div>
                    )}
                    <CommandEmpty>{t('contracts.merge.noContracts')}</CommandEmpty>
                    <CommandGroup>
                      {eligibleContracts.map((c: { id: string; name: string; status: string }) => (
                        <CommandItem
                          key={c.id}
                          value={c.id}
                          onSelect={() => {
                            setTargetContractId(c.id)
                            setContractSearchOpen(false)
                          }}
                        >
                          <Check
                            className={cn(
                              'mr-2 h-4 w-4',
                              targetContractId === c.id ? 'opacity-100' : 'opacity-0'
                            )}
                          />
                          <div className="flex flex-col">
                            <span>{c.name || `Contract #${c.id}`}</span>
                            <span className="text-xs text-muted-foreground">{c.status}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Preview Loading */}
          {loadingPreview && targetContractId && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          )}

          {/* Preview Errors */}
          {preview?.errors?.length > 0 && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              {preview.errors.join('; ')}
            </div>
          )}

          {/* Items Preview */}
          {previewItems.length > 0 && (
            <div className="space-y-2">
              <Label>{t('contracts.merge.itemsToTransfer')}</Label>
              <div className="rounded border">
                <table className="w-full text-sm">
                  <thead className="bg-muted/50">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">{t('contracts.merge.item')}</th>
                      <th className="px-3 py-2 text-left font-medium">{t('contracts.merge.qty')}</th>
                      <th className="px-3 py-2 text-left font-medium">{t('contracts.merge.price')}</th>
                      <th className="px-3 py-2 text-left font-medium">{t('contracts.merge.startDate')}</th>
                      <th className="px-3 py-2 text-left font-medium">{t('contracts.merge.billingStart')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewItems.map((item) => (
                      <tr key={item.id} className="border-t">
                        <td className="px-3 py-2">
                          <div className="flex flex-col">
                            <span>{item.productName || item.description}</span>
                            {item.isOneOff && (
                              <span className="text-xs text-muted-foreground">{t('contracts.merge.oneOff')}</span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2">{item.quantity}</td>
                        <td className="px-3 py-2">
                          {parseFloat(item.unitPrice).toLocaleString('de-DE', { minimumFractionDigits: 2 })} / {item.pricePeriod}
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="date"
                            className="h-8 w-36"
                            defaultValue={item.startDate || ''}
                            onChange={(e) => updateOverride(item.id, 'startDate', e.target.value)}
                          />
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="date"
                            className="h-8 w-36"
                            defaultValue={item.billingStartDate || ''}
                            onChange={(e) => updateOverride(item.id, 'billingStartDate', e.target.value)}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Amendment Info */}
          {preview && !preview.errors?.length && (
            <div className={cn(
              'rounded border p-3 text-sm',
              preview.willCreateAmendments
                ? 'border-amber-200 bg-amber-50 text-amber-800'
                : 'border-blue-200 bg-blue-50 text-blue-800'
            )}>
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  {preview.willCreateAmendments
                    ? t('contracts.merge.amendmentsWillBeCreated')
                    : t('contracts.merge.noAmendments')}
                </span>
              </div>
            </div>
          )}

          {/* Clockodo Preview */}
          {preview?.clockodoPreview && (
            <div className="rounded border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
              <p className="font-medium">{t('contracts.merge.clockodoImpact')}</p>
              {preview.clockodoPreview.hasNewRecurringItems && (
                <p>{t('contracts.merge.clockodoNewRecurring')}</p>
              )}
              {preview.clockodoPreview.newOneOffItems?.length > 0 && (
                <p>{t('contracts.merge.clockodoNewOneOff', { count: preview.clockodoPreview.newOneOffItems.length })}</p>
              )}
              {preview.clockodoPreview.sourceMappingsWillBeDeleted > 0 && (
                <p>{t('contracts.merge.clockodoMappingsDeleted', { count: preview.clockodoPreview.sourceMappingsWillBeDeleted })}</p>
              )}
            </div>
          )}

          {/* Irreversible Warning */}
          {targetContractId && preview && !preview.errors?.length && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{t('contracts.merge.warningIrreversible')}</span>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
              {error}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('contracts.actions.cancel')}
          </Button>
          <Button
            onClick={handleMerge}
            disabled={!targetContractId || merging || loadingPreview || (preview?.errors?.length > 0)}
            data-testid="merge-confirm-button"
          >
            {merging && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            <GitMerge className="mr-2 h-4 w-4" />
            {t('contracts.merge.confirmButton')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
