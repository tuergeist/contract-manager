import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useLazyQuery, gql } from '@apollo/client'
import { Loader2, Search, Unlink } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { formatCurrency, formatDate } from '@/lib/utils'

// --- GraphQL ---

const FIND_PAYMENT_MATCHES = gql`
  query FindPaymentMatchesShared($invoiceId: ID!, $daysAfter: Int) {
    findPaymentMatches(invoiceId: $invoiceId, daysAfter: $daysAfter) {
      transactionId
      transactionDate
      amount
      counterpartyName
      bookingText
      matchType
      confidence
    }
  }
`

const FIND_PAYMENT_MATCHES_FOR_RECORD = gql`
  query FindPaymentMatchesForRecordShared($invoiceRecordId: Int!, $daysAfter: Int) {
    findPaymentMatchesForRecord(invoiceRecordId: $invoiceRecordId, daysAfter: $daysAfter) {
      transactionId
      transactionDate
      amount
      counterpartyName
      bookingText
      matchType
      confidence
    }
  }
`

const SEARCH_TRANSACTIONS = gql`
  query SearchTransactionsShared($search: String, $direction: String, $page: Int, $pageSize: Int) {
    bankTransactions(search: $search, direction: $direction, page: $page, pageSize: $pageSize) {
      items {
        id
        entryDate
        amount
        currency
        counterparty {
          name
        }
        bookingText
      }
      totalCount
    }
  }
`

const CREATE_PAYMENT_MATCH = gql`
  mutation CreatePaymentMatchShared($invoiceId: ID!, $transactionId: Int!, $matchType: String) {
    createPaymentMatch(invoiceId: $invoiceId, transactionId: $transactionId, matchType: $matchType) {
      success
      error
      match {
        id
        transactionId
        transactionDate
        transactionAmount
        counterpartyName
        matchType
        confidence
      }
    }
  }
`

const CREATE_PAYMENT_MATCH_FOR_RECORD = gql`
  mutation CreatePaymentMatchForRecordShared($invoiceRecordId: Int!, $transactionId: Int!, $matchType: String) {
    createPaymentMatchForRecord(invoiceRecordId: $invoiceRecordId, transactionId: $transactionId, matchType: $matchType) {
      success
      error
      match {
        id
        transactionId
        transactionDate
        transactionAmount
        counterpartyName
        matchType
        confidence
      }
    }
  }
`

const DELETE_PAYMENT_MATCH = gql`
  mutation DeletePaymentMatchShared($matchId: Int!) {
    deletePaymentMatch(matchId: $matchId) {
      success
      error
    }
  }
`

// --- Types ---

interface PaymentMatch {
  id: number
  transactionId: number
  transactionDate: string
  transactionAmount: string
  counterpartyName: string
  matchType: string
  confidence: string
}

interface PaymentMatchCandidate {
  transactionId: number
  transactionDate: string
  amount: string
  counterpartyName: string
  bookingText: string
  matchType: string
  confidence: string
}

interface SearchTransaction {
  id: number
  entryDate: string
  amount: string
  currency: string
  counterparty: { name: string } | null
  bookingText: string
}

interface PaymentMatchModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** For imported invoices */
  invoiceId?: string
  /** For generated invoice records */
  invoiceRecordId?: number
  /** Display info */
  invoiceNumber: string
  amount: string | null
  customerName: string
  isPaid: boolean
  existingMatches: PaymentMatch[]
  onMatchChanged: () => void
}

// --- Component ---

export function PaymentMatchModal({
  open,
  onOpenChange,
  invoiceId,
  invoiceRecordId,
  invoiceNumber,
  amount,
  customerName,
  isPaid,
  existingMatches,
  onMatchChanged,
}: PaymentMatchModalProps) {
  const { t } = useTranslation()

  const [transactionSearch, setTransactionSearch] = useState('')
  const [debouncedTxSearch, setDebouncedTxSearch] = useState('')

  // Reset search on close
  useEffect(() => {
    if (!open) {
      setTransactionSearch('')
      setDebouncedTxSearch('')
    }
  }, [open])

  // Debounce
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedTxSearch(transactionSearch), 300)
    return () => clearTimeout(timer)
  }, [transactionSearch])

  // Fetch suggested matches
  const [findMatches, { data: matchData, loading: loadingMatches }] = useLazyQuery(
    invoiceId ? FIND_PAYMENT_MATCHES : FIND_PAYMENT_MATCHES_FOR_RECORD,
    { fetchPolicy: 'network-only' }
  )

  useEffect(() => {
    if (open) {
      if (invoiceId) {
        findMatches({ variables: { invoiceId, daysAfter: 90 } })
      } else if (invoiceRecordId) {
        findMatches({ variables: { invoiceRecordId, daysAfter: 90 } })
      }
    }
  }, [open, invoiceId, invoiceRecordId, findMatches])

  // Manual search
  const { data: searchTxData, loading: loadingTxSearch } = useQuery(SEARCH_TRANSACTIONS, {
    variables: { search: debouncedTxSearch, direction: 'credit', page: 1, pageSize: 20 },
    skip: !open || !debouncedTxSearch,
  })

  // Mutations
  const [createMatch] = useMutation(invoiceId ? CREATE_PAYMENT_MATCH : CREATE_PAYMENT_MATCH_FOR_RECORD)
  const [deleteMatch] = useMutation(DELETE_PAYMENT_MATCH)

  const suggestedMatches: PaymentMatchCandidate[] = invoiceId
    ? matchData?.findPaymentMatches || []
    : matchData?.findPaymentMatchesForRecord || []

  const handleCreate = async (transactionId: number, matchType: string = 'manual') => {
    const variables = invoiceId
      ? { invoiceId, transactionId, matchType }
      : { invoiceRecordId, transactionId, matchType }

    const result = await createMatch({ variables })
    const success = invoiceId
      ? result.data?.createPaymentMatch?.success
      : result.data?.createPaymentMatchForRecord?.success

    if (success) {
      onOpenChange(false)
      onMatchChanged()
    }
  }

  const handleDelete = async (matchId: number) => {
    const result = await deleteMatch({ variables: { matchId } })
    if (result.data?.deletePaymentMatch?.success) {
      onMatchChanged()
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>{t('invoices.import.matchPaymentTitle')}</DialogTitle>
          <DialogDescription>
            {t('invoices.import.matchPaymentDescription', {
              invoiceNumber,
              amount: amount ? formatCurrency(parseFloat(amount)) : '-',
              customer: customerName || '-',
            })}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          {/* Existing matches */}
          {existingMatches.length > 0 && (
            <div>
              <h4 className="mb-2 text-sm font-medium text-gray-700">{t('invoices.import.existingMatches')}</h4>
              <div className="space-y-2">
                {existingMatches.map((match) => (
                  <div
                    key={match.id}
                    className="flex items-center justify-between rounded-lg border border-green-200 bg-green-50 p-3"
                  >
                    <div>
                      <div className="font-medium">{match.counterpartyName}</div>
                      <div className="text-sm text-gray-500">
                        {formatDate(match.transactionDate)} - {formatCurrency(parseFloat(match.transactionAmount))}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">{match.matchType}</Badge>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(match.id)}
                        className="text-red-600 hover:bg-red-50 hover:text-red-700"
                      >
                        <Unlink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested matches */}
          {!isPaid && (
            <>
              <div>
                <h4 className="mb-2 text-sm font-medium text-gray-700">{t('invoices.import.suggestedMatches')}</h4>
                {loadingMatches ? (
                  <div className="py-4 text-center">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin" />
                  </div>
                ) : suggestedMatches.length ? (
                  <div className="max-h-48 space-y-2 overflow-y-auto">
                    {suggestedMatches.map((match) => (
                      <button
                        key={match.transactionId}
                        onClick={() => handleCreate(match.transactionId, match.matchType)}
                        className="w-full rounded-lg border p-3 text-left hover:bg-gray-50"
                      >
                        <div className="flex items-center justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="font-medium">{match.counterpartyName}</div>
                            <div className="break-words text-sm text-gray-500">
                              {formatDate(match.transactionDate)} - {match.bookingText}
                            </div>
                          </div>
                          <div className="ml-4 flex flex-col items-end">
                            <span className="font-mono text-green-600">
                              {formatCurrency(parseFloat(match.amount))}
                            </span>
                            <div className="flex items-center gap-1">
                              <Badge variant="outline" className="text-xs">{match.matchType}</Badge>
                              <span className="text-xs text-gray-400">
                                {Math.round(parseFloat(match.confidence) * 100)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="py-2 text-center text-sm text-gray-500">{t('invoices.import.noSuggestedMatches')}</p>
                )}
              </div>

              {/* Manual search */}
              <div>
                <h4 className="mb-2 text-sm font-medium text-gray-700">{t('invoices.import.manualSearch')}</h4>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <Input
                    value={transactionSearch}
                    onChange={(e) => setTransactionSearch(e.target.value)}
                    placeholder={t('invoices.import.searchTransactions')}
                    className="pl-9"
                  />
                </div>
                {loadingTxSearch ? (
                  <div className="py-2 text-center">
                    <Loader2 className="mx-auto h-4 w-4 animate-spin" />
                  </div>
                ) : debouncedTxSearch && (searchTxData?.bankTransactions?.items as SearchTransaction[] | undefined)?.length ? (
                  <div className="mt-2 max-h-48 space-y-2 overflow-y-auto">
                    {(searchTxData.bankTransactions.items as SearchTransaction[]).map((tx) => (
                      <button
                        key={tx.id}
                        onClick={() => handleCreate(tx.id, 'manual')}
                        className="w-full rounded-lg border p-3 text-left hover:bg-gray-50"
                      >
                        <div className="flex items-center justify-between">
                          <div className="min-w-0 flex-1">
                            <div className="font-medium">{tx.counterparty?.name || '-'}</div>
                            <div className="break-words text-sm text-gray-500">
                              {formatDate(tx.entryDate)} - {tx.bookingText}
                            </div>
                          </div>
                          <span className="ml-4 font-mono text-green-600">
                            {formatCurrency(parseFloat(tx.amount))}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : debouncedTxSearch ? (
                  <p className="mt-2 py-2 text-center text-sm text-gray-500">{t('invoices.import.noTransactionsFound')}</p>
                ) : null}
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
