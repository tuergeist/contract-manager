import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Check, ChevronsUpDown, MoveRight } from 'lucide-react'
import { cn, formatDate } from '@/lib/utils'
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

const TARGET_CONTRACTS_QUERY = gql`
  query MoveItemTargetContracts($search: String, $status: String, $page: Int, $pageSize: Int) {
    contracts(search: $search, status: $status, page: $page, pageSize: $pageSize) {
      items {
        id
        name
        status
        billingInterval
        customer {
          id
          name
        }
      }
    }
  }
`

const MOVE_ITEM_MUTATION = gql`
  mutation MoveContractItem($input: MoveContractItemInput!) {
    moveContractItem(input: $input) {
      success
      error
      sourceItem {
        id
        billingEndDate
      }
      newItem {
        id
        billingStartDate
      }
    }
  }
`

interface ContractItem {
  id: string
  product?: { id: string; name: string } | null
  description?: string
  quantity: number
  unitPrice: string
  pricePeriod: string
}

interface SourceContract {
  id: string
  name: string
  customer: { id: string; name: string }
  status: string
}

interface MoveItemDialogProps {
  item: ContractItem
  sourceContract: SourceContract
  onClose: () => void
  onSuccess: () => void
}

export function MoveItemDialog({
  item,
  sourceContract,
  onClose,
  onSuccess,
}: MoveItemDialogProps) {
  const { t } = useTranslation()

  const [targetContractId, setTargetContractId] = useState<string | null>(null)
  const [contractSearchOpen, setContractSearchOpen] = useState(false)
  const [contractSearchTerm, setContractSearchTerm] = useState('')
  const [effectiveDate, setEffectiveDate] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: contractsData } = useQuery(TARGET_CONTRACTS_QUERY, {
    variables: { search: contractSearchTerm || sourceContract.customer.name, pageSize: 50 },
  })

  const eligibleContracts = (contractsData?.contracts?.items || []).filter(
    (c: { id: string; status: string; customer: { id: string } }) =>
      c.customer.id === sourceContract.customer.id &&
      c.id !== sourceContract.id &&
      !['deleted', 'cancelled', 'ended'].includes(c.status)
  )

  const selectedContract = eligibleContracts.find((c: { id: string }) => c.id === targetContractId)

  const [moveItem, { loading }] = useMutation(MOVE_ITEM_MUTATION)

  const itemName = item.product?.name || item.description || '-'

  const handleMove = async () => {
    if (!targetContractId || !effectiveDate) return
    setError(null)

    try {
      const { data } = await moveItem({
        variables: {
          input: {
            itemId: item.id,
            targetContractId,
            effectiveDate,
          },
        },
      })
      if (data?.moveContractItem?.success) {
        onSuccess()
      } else {
        setError(data?.moveContractItem?.error || t('contracts.moveItem.errorGeneric'))
      }
    } catch {
      setError(t('contracts.moveItem.errorGeneric'))
    }
  }

  // Compute next-day billing start for preview
  const billingStart = effectiveDate
    ? formatDate(new Date(new Date(effectiveDate).getTime() + 86400000).toISOString().slice(0, 10))
    : null

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MoveRight className="h-5 w-5" />
            {t('contracts.moveItem.title')}
          </DialogTitle>
          <DialogDescription>
            {t('contracts.moveItem.description', { name: itemName })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Target contract selector */}
          <div className="space-y-2">
            <Label>{t('contracts.moveItem.targetLabel')}</Label>
            <Popover open={contractSearchOpen} onOpenChange={setContractSearchOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  role="combobox"
                  className="w-full justify-between font-normal"
                >
                  {selectedContract
                    ? selectedContract.name
                    : t('contracts.moveItem.selectTarget')}
                  <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-[400px] p-0" align="start">
                <Command shouldFilter={false}>
                  <CommandInput
                    placeholder={t('contracts.moveItem.searchPlaceholder')}
                    value={contractSearchTerm}
                    onValueChange={setContractSearchTerm}
                  />
                  <CommandList>
                    <CommandEmpty>{t('contracts.moveItem.noContracts')}</CommandEmpty>
                    <CommandGroup>
                      {eligibleContracts.map((c: { id: string; name: string; status: string; billingInterval: string }) => (
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
                          <div>
                            <div>{c.name}</div>
                            <div className="text-xs text-gray-500">{c.status} • {c.billingInterval}</div>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </CommandList>
                </Command>
              </PopoverContent>
            </Popover>
          </div>

          {/* Effective date */}
          <div className="space-y-2">
            <Label>{t('contracts.moveItem.effectiveDate')}</Label>
            <Input
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
            />
            <p className="text-xs text-gray-500">
              {t('contracts.moveItem.effectiveDateHelp')}
            </p>
          </div>

          {/* Preview */}
          {effectiveDate && targetContractId && (
            <div className="rounded-md border bg-gray-50 p-3 text-sm space-y-1">
              <div className="font-medium">{t('contracts.moveItem.preview')}</div>
              <div className="text-gray-600">
                {t('contracts.moveItem.sourceWillEnd', { date: formatDate(effectiveDate) })}
              </div>
              <div className="text-gray-600">
                {t('contracts.moveItem.targetWillStart', { date: billingStart })}
              </div>
              {sourceContract.status !== 'draft' && (
                <div className="text-amber-600 text-xs mt-2">
                  {t('contracts.moveItem.amendmentsWillBeCreated')}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-md p-3">{error}</div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={handleMove}
            disabled={!targetContractId || !effectiveDate || loading}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('contracts.moveItem.confirmButton')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
