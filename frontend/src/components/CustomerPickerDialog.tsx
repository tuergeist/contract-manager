import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Search, Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const SEARCH_CUSTOMERS = gql`
  query SearchCustomersForPicker($search: String!) {
    customers(search: $search) {
      items {
        id
        name
        address
      }
    }
  }
`

interface CustomerPickerDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description?: string
  onSelect: (customerId: number, customerName?: string) => void | Promise<void>
  loading?: boolean
  children?: React.ReactNode
}

export function CustomerPickerDialog({
  open,
  onOpenChange,
  title,
  description,
  onSelect,
  loading: externalLoading,
  children,
}: CustomerPickerDialogProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  // Reset search when dialog closes
  useEffect(() => {
    if (!open) {
      setSearch('')
      setDebouncedSearch('')
    }
  }, [open])

  const { data, loading: searchLoading } = useQuery(SEARCH_CUSTOMERS, {
    variables: { search: debouncedSearch },
    skip: !open || !debouncedSearch || debouncedSearch.length < 2,
  })

  const showResults = debouncedSearch && debouncedSearch.length >= 2

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="py-4 space-y-4">
          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('common.customerPicker.searchPlaceholder')}
              className="pl-9"
              disabled={externalLoading}
            />
          </div>

          {/* Search results */}
          {showResults && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                {t('common.customerPicker.searchResults')}
              </h4>
              {searchLoading ? (
                <div className="text-center py-2">
                  <Loader2 className="w-4 h-4 mx-auto animate-spin" />
                </div>
              ) : data?.customers?.items?.length > 0 ? (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {data.customers.items.map(
                    (customer: {
                      id: number
                      name: string
                      address?: { city?: string | null } | null
                    }) => (
                      <button
                        key={customer.id}
                        onClick={() => onSelect(customer.id, customer.name)}
                        disabled={externalLoading}
                        className="w-full flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 text-left disabled:opacity-50"
                      >
                        <div>
                          <div className="font-medium">{customer.name}</div>
                          <div className="text-xs text-gray-500">
                            CUS-{customer.id}
                            {customer.address?.city &&
                              ` · ${customer.address.city}`}
                          </div>
                        </div>
                      </button>
                    )
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-500 text-center py-2">
                  {t('common.customerPicker.noResults')}
                </p>
              )}
            </div>
          )}

          {/* Children (e.g. suggestions) shown when not searching */}
          {!showResults && children}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            {t('common.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
