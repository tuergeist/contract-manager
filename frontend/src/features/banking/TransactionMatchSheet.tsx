import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Search, Unlink, FileText, CheckCircle2 } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { formatCurrency, formatDate } from '@/lib/utils'

// --- GraphQL ---

const TRANSACTION_MATCH_DETAILS = gql`
  query TransactionMatchDetails($transactionId: Int!) {
    transactionMatchDetails(transactionId: $transactionId) {
      id
      entryDate
      valueDate
      amount
      currency
      counterpartyName
      bookingText
      reference
      accountName
      totalMatched
      difference
      customerId
      matches {
        id
        invoiceId
        invoiceRecordId
        invoiceNumber
        invoiceAmount
        customerName
        invoiceType
        matchType
        confidence
        matchedAt
      }
    }
  }
`

const BANKING_SETTINGS_FOR_MATCH = gql`
  query BankingSettingsForMatch {
    bankingSettings {
      feeToleranceFixed
      feeTolerancePercent
    }
  }
`

const SEARCH_INVOICES_FOR_MATCHING = gql`
  query SearchInvoicesForMatching($search: String!, $unmatchedOnly: Boolean, $limit: Int) {
    searchInvoicesForMatching(search: $search, unmatchedOnly: $unmatchedOnly, limit: $limit) {
      items {
        id
        invoiceNumber
        amount
        customerName
        invoiceType
        status
        invoiceDate
        isPaid
      }
      hasMore
    }
  }
`

const CREATE_PAYMENT_MATCH = gql`
  mutation CreatePaymentMatchFromSheet($invoiceId: ID!, $transactionId: Int!, $matchType: String) {
    createPaymentMatch(invoiceId: $invoiceId, transactionId: $transactionId, matchType: $matchType) {
      success
      error
    }
  }
`

const CREATE_PAYMENT_MATCH_FOR_RECORD = gql`
  mutation CreatePaymentMatchForRecordFromSheet($invoiceRecordId: Int!, $transactionId: Int!, $matchType: String) {
    createPaymentMatchForRecord(invoiceRecordId: $invoiceRecordId, transactionId: $transactionId, matchType: $matchType) {
      success
      error
    }
  }
`

const DELETE_PAYMENT_MATCH = gql`
  mutation DeletePaymentMatchFromSheet($matchId: Int!) {
    deletePaymentMatch(matchId: $matchId) {
      success
      error
    }
  }
`

const SUGGESTED_INVOICE_MATCHES = gql`
  query SuggestedInvoiceMatches($transactionId: Int!) {
    suggestedInvoiceMatches(transactionId: $transactionId) {
      customerName
      customerId
      items {
        id
        invoiceNumber
        amount
        customerName
        invoiceType
        status
        invoiceDate
        isPaid
        amountDifference
      }
    }
  }
`

// --- Types ---

interface MatchDetail {
  id: number
  invoiceId: string | null
  invoiceRecordId: number | null
  invoiceNumber: string
  invoiceAmount: string
  customerName: string
  invoiceType: 'imported' | 'generated'
  matchType: string
  confidence: string
  matchedAt: string
}

interface TransactionMatchData {
  id: number
  entryDate: string
  valueDate: string | null
  amount: string
  currency: string
  counterpartyName: string
  bookingText: string
  reference: string
  accountName: string
  totalMatched: string
  difference: string
  customerId: number | null
  matches: MatchDetail[]
}

interface SuggestedMatch extends InvoiceSearchResult {
  amountDifference: string
}

interface SuggestedMatchesData {
  customerName: string
  customerId: number
  items: SuggestedMatch[]
}

interface InvoiceSearchResult {
  id: string
  invoiceNumber: string
  amount: string
  customerName: string
  invoiceType: 'imported' | 'generated'
  status: string
  invoiceDate: string | null
  isPaid: boolean
}

interface Props {
  transactionId: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onMatchChanged?: () => void
}

export function TransactionMatchSheet({ transactionId, open, onOpenChange, onMatchChanged }: Props) {
  const { t } = useTranslation()
  const [searchText, setSearchText] = useState('')
  const [unmatchedOnly, setUnmatchedOnly] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const { data, loading, refetch } = useQuery(TRANSACTION_MATCH_DETAILS, {
    variables: { transactionId },
    skip: !transactionId || !open,
    fetchPolicy: 'network-only',
  })

  const { data: settingsData } = useQuery(BANKING_SETTINGS_FOR_MATCH)

  const customerId = data?.transactionMatchDetails?.customerId ?? null

  const { data: suggestionsData, loading: suggestionsLoading, refetch: refetchSuggestions } = useQuery(SUGGESTED_INVOICE_MATCHES, {
    variables: { transactionId },
    skip: !transactionId || !open || customerId === null,
    fetchPolicy: 'network-only',
  })

  const { data: searchData, loading: searchLoading } = useQuery(SEARCH_INVOICES_FOR_MATCHING, {
    variables: { search: searchText, unmatchedOnly, limit: 20 },
    skip: !searchText || searchText.length < 2,
    fetchPolicy: 'network-only',
  })

  const [createMatch] = useMutation(CREATE_PAYMENT_MATCH)
  const [createMatchForRecord] = useMutation(CREATE_PAYMENT_MATCH_FOR_RECORD)
  const [deleteMatch] = useMutation(DELETE_PAYMENT_MATCH)

  const txn: TransactionMatchData | null = data?.transactionMatchDetails ?? null
  const suggestions: SuggestedMatchesData | null = suggestionsData?.suggestedInvoiceMatches ?? null

  const handleAddMatch = async (invoice: InvoiceSearchResult) => {
    if (!transactionId) return
    setError(null)

    try {
      let result
      if (invoice.invoiceType === 'imported') {
        result = await createMatch({
          variables: { invoiceId: invoice.id, transactionId, matchType: 'manual' },
        })
        result = result.data.createPaymentMatch
      } else {
        result = await createMatchForRecord({
          variables: { invoiceRecordId: parseInt(invoice.id), transactionId, matchType: 'manual' },
        })
        result = result.data.createPaymentMatchForRecord
      }

      if (result.success) {
        refetch()
        if (customerId !== null) refetchSuggestions()
        onMatchChanged?.()
      } else {
        setError(result.error || 'Failed to create match')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create match')
    }
  }

  const handleRemoveMatch = async (matchId: number) => {
    setError(null)
    try {
      const { data: result } = await deleteMatch({ variables: { matchId } })
      if (result.deletePaymentMatch.success) {
        refetch()
        onMatchChanged?.()
      } else {
        setError(result.deletePaymentMatch.error || 'Failed to remove match')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to remove match')
    }
  }

  // Calculate difference status
  const getDifferenceStatus = () => {
    if (!txn || txn.matches.length === 0) return 'neutral'
    const diff = parseFloat(txn.difference)
    const txnAmount = Math.abs(parseFloat(txn.amount))
    const totalMatched = parseFloat(txn.totalMatched)
    if (txnAmount === 0) return 'neutral'

    // Underpaid: transaction amount > total matched invoices
    if (diff > 0) return 'underpaid'

    // Exact match (rounding)
    if (Math.abs(diff) <= 0.01) return 'matched'

    // Configurable tolerance: fixed + percent of matched total
    const tolFixed = parseFloat(settingsData?.bankingSettings?.feeToleranceFixed ?? '0')
    const tolPercent = parseFloat(settingsData?.bankingSettings?.feeTolerancePercent ?? '0')
    const tolerance = tolFixed + (totalMatched * tolPercent / 100)

    if (Math.abs(diff) <= tolerance) return 'matched'
    return 'overbooking'
  }

  const diffStatus = getDifferenceStatus()

  // Check if matched within tolerance (has a difference but still considered matched)
  const isWithinTolerance = () => {
    if (!txn || diffStatus !== 'matched') return false
    const diff = parseFloat(txn.difference)
    return Math.abs(diff) > 0.01
  }

  const searchResults: InvoiceSearchResult[] = searchData?.searchInvoicesForMatching?.items ?? []
  // Filter out already matched invoices from search results
  const matchedIds = new Set(
    (txn?.matches ?? []).map(m =>
      m.invoiceType === 'imported' ? `imported-${m.invoiceId}` : `generated-${m.invoiceRecordId}`
    )
  )
  const filteredResults = searchResults.filter(inv => {
    const key = inv.invoiceType === 'imported' ? `imported-${inv.id}` : `generated-${inv.id}`
    return !matchedIds.has(key)
  })

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t('banking.matchView.title')}</SheetTitle>
          <SheetDescription className="sr-only">
            {t('banking.matchView.title')}
          </SheetDescription>
        </SheetHeader>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        )}

        {txn && (
          <div className="mt-4 space-y-6">
            {/* Transaction Summary */}
            <div className="rounded-lg border bg-gray-50 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">{formatDate(txn.entryDate)}</span>
                <span className={`text-lg font-bold ${parseFloat(txn.amount) >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {formatCurrency(txn.amount, { currency: txn.currency })}
                </span>
              </div>
              <div className="text-sm font-medium">{txn.counterpartyName}</div>
              {txn.bookingText && (
                <div className="text-xs text-gray-500 line-clamp-2">{txn.bookingText}</div>
              )}
              {txn.reference && (
                <div className="text-xs text-gray-400">Ref: {txn.reference}</div>
              )}
              <div className="text-xs text-gray-400">
                {txn.accountName}
                {txn.valueDate && ` | ${t('banking.valueDate')}: ${formatDate(txn.valueDate)}`}
              </div>
            </div>

            {/* Difference Banner */}
            <div className={`rounded-lg border p-3 text-sm ${
              diffStatus === 'matched' ? 'border-green-200 bg-green-50 text-green-800' :
              diffStatus === 'underpaid' ? 'border-yellow-200 bg-yellow-50 text-yellow-800' :
              diffStatus === 'overbooking' ? 'border-orange-200 bg-orange-50 text-orange-800' :
              'border-gray-200 bg-gray-50 text-gray-600'
            }`}>
              <div className="flex items-center justify-between">
                <span>{t('banking.matchView.totalMatched')}: {formatCurrency(txn.totalMatched, { currency: txn.currency })}</span>
                <span className="font-medium">
                  {diffStatus === 'matched' && !isWithinTolerance() && t('banking.matchView.fullyMatched')}
                  {diffStatus === 'matched' && isWithinTolerance() && (
                    <>
                      {t('banking.matchView.fullyMatched')}
                      {' '}
                      <span className="text-xs font-normal">
                        ({formatCurrency(txn.difference, { currency: txn.currency })} {t('banking.matchView.withinTolerance')})
                      </span>
                    </>
                  )}
                  {diffStatus === 'underpaid' && `${formatCurrency(txn.difference, { currency: txn.currency })} ${t('banking.matchView.remaining')}`}
                  {diffStatus === 'overbooking' && `${formatCurrency(txn.difference, { currency: txn.currency })}`}
                </span>
              </div>
              {diffStatus === 'overbooking' && (
                <div className="mt-1 text-xs font-medium">
                  {t('banking.matchView.overbookingWarning')}
                </div>
              )}
            </div>

            {/* Error display */}
            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </div>
            )}

            {/* Matched Invoices */}
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">
                {t('banking.matchView.matchedInvoices')} ({txn.matches.length})
              </h3>
              {txn.matches.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-4 text-center text-sm text-gray-500">
                  <FileText className="mx-auto h-8 w-8 text-gray-300 mb-2" />
                  {t('banking.matchView.noMatches')}
                </div>
              ) : (
                <div className="space-y-2">
                  {txn.matches.map(match => (
                    <div key={match.id} className="flex items-center justify-between rounded-lg border bg-white p-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{match.invoiceNumber}</span>
                          <Badge variant="outline" className="text-xs shrink-0">
                            {match.invoiceType === 'imported'
                              ? t('banking.matchView.imported')
                              : t('banking.matchView.generated')}
                          </Badge>
                        </div>
                        <div className="text-xs text-gray-500 truncate">{match.customerName}</div>
                      </div>
                      <div className="flex items-center gap-2 ml-2 shrink-0">
                        <span className="text-sm font-medium">{formatCurrency(match.invoiceAmount)}</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 w-7 p-0 text-gray-400 hover:text-red-600"
                          onClick={() => handleRemoveMatch(match.id)}
                          title={t('banking.matchView.removeMatch')}
                        >
                          <Unlink className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Suggested Matches */}
            {customerId !== null && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">
                  {t('banking.matchView.suggestedMatches')}
                  {suggestions && ` — ${suggestions.customerName}`}
                </h3>

                {suggestionsLoading && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                  </div>
                )}

                {!suggestionsLoading && suggestions && suggestions.items.length === 0 && (
                  <div className="rounded-lg border border-dashed border-gray-300 p-3 text-center text-sm text-gray-500">
                    {t('banking.matchView.allSuggestionsMatched')}
                  </div>
                )}

                {!suggestionsLoading && suggestions && suggestions.items.length > 0 && (
                  <div className="space-y-1">
                    {suggestions.items.map(inv => {
                      const diff = parseFloat(inv.amountDifference)
                      const isExact = Math.abs(diff) < 0.01
                      return (
                        <button
                          key={`${inv.invoiceType}-${inv.id}`}
                          className={`w-full flex items-center justify-between rounded-lg border p-2.5 text-left transition-colors ${
                            isExact
                              ? 'border-green-300 bg-green-50 hover:bg-green-100'
                              : 'border-gray-200 bg-white hover:bg-blue-50 hover:border-blue-200'
                          }`}
                          onClick={() => handleAddMatch(inv)}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium truncate">{inv.invoiceNumber}</span>
                              <Badge variant="outline" className="text-xs shrink-0">
                                {inv.invoiceType === 'imported'
                                  ? t('banking.matchView.imported')
                                  : t('banking.matchView.generated')}
                              </Badge>
                              {isExact && (
                                <Badge className="text-xs shrink-0 bg-green-600 text-white hover:bg-green-600">
                                  <CheckCircle2 className="h-3 w-3 mr-0.5" />
                                  {t('banking.matchView.exactMatch')}
                                </Badge>
                              )}
                            </div>
                            <div className="text-xs text-gray-500 truncate">
                              {inv.invoiceDate && formatDate(inv.invoiceDate)}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 ml-2 shrink-0">
                            {!isExact && (
                              <span className={`text-xs ${diff > 0 ? 'text-orange-600' : 'text-blue-600'}`}>
                                {diff > 0 ? '+' : ''}{formatCurrency(inv.amountDifference)}
                              </span>
                            )}
                            <span className="text-sm font-medium">
                              {formatCurrency(inv.amount)}
                            </span>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Invoice Search */}
            <div className="border-t pt-4">
              <div className="flex items-center gap-3 mb-3">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder={t('banking.matchView.searchInvoices')}
                    value={searchText}
                    onChange={e => setSearchText(e.target.value)}
                    className="pl-9"
                  />
                </div>
                <div className="flex items-center gap-1.5">
                  <Switch
                    id="unmatched-only"
                    checked={unmatchedOnly}
                    onCheckedChange={setUnmatchedOnly}
                  />
                  <Label htmlFor="unmatched-only" className="text-xs whitespace-nowrap">
                    {t('banking.matchView.unmatchedOnly')}
                  </Label>
                </div>
              </div>

              {searchLoading && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
                </div>
              )}

              {searchText.length >= 2 && !searchLoading && filteredResults.length === 0 && (
                <div className="text-center text-sm text-gray-500 py-4">
                  {t('banking.matchView.noResults')}
                </div>
              )}

              {filteredResults.length > 0 && (
                <div className="space-y-1 max-h-60 overflow-y-auto">
                  {filteredResults.map(inv => (
                    <button
                      key={`${inv.invoiceType}-${inv.id}`}
                      className="w-full flex items-center justify-between rounded-lg border border-gray-200 bg-white p-2.5 text-left hover:bg-blue-50 hover:border-blue-200 transition-colors"
                      onClick={() => handleAddMatch(inv)}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{inv.invoiceNumber}</span>
                          <Badge variant="outline" className="text-xs shrink-0">
                            {inv.invoiceType === 'imported'
                              ? t('banking.matchView.imported')
                              : t('banking.matchView.generated')}
                          </Badge>
                          {inv.isPaid && (
                            <Badge className="text-xs shrink-0 bg-green-100 text-green-800 hover:bg-green-100">
                              Paid
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 truncate">
                          {inv.customerName}
                          {inv.invoiceDate && ` | ${formatDate(inv.invoiceDate)}`}
                        </div>
                      </div>
                      <span className="text-sm font-medium ml-2 shrink-0">
                        {formatCurrency(inv.amount)}
                      </span>
                    </button>
                  ))}
                  {searchData?.searchInvoicesForMatching?.hasMore && (
                    <div className="text-center text-xs text-gray-400 py-1">
                      ...
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
