import { useState, useCallback, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useLazyQuery, gql } from '@apollo/client'
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Search,
} from 'lucide-react'

const UPLOAD_CONTRACT_IMPORT = gql`
  mutation UploadContractImport($fileContent: String!, $filename: String!, $autoApproveThreshold: Float) {
    uploadContractImport(fileContent: $fileContent, filename: $filename, autoApproveThreshold: $autoApproveThreshold) {
      success
      error
      session {
        id
        summary {
          totalProposals
          autoMatched
          needsReview
          notFound
          totalItems
          alreadyImported
        }
        proposals {
          id
          customerNumber
          customerName
          salesOrderNumber
          contractNumber
          startDate
          endDate
          invoicingInstructions
          matchResult {
            status
            customerId
            customerName
            customerCity
            confidence
            originalName
            alternatives {
              customerId
              customerName
              customerCity
              confidence
            }
          }
          selectedCustomerId
          items {
            itemName
            monthlyRate
            productId
            productName
          }
          discountAmount
          totalMonthlyRate
          approved
          rejected
          error
          needsReview
          existingContractId
        }
        parserErrors
      }
    }
  }
`

const REVIEW_IMPORT_PROPOSALS = gql`
  mutation ReviewImportProposals($sessionId: String!, $reviews: [ReviewProposalInput!]!) {
    reviewImportProposals(sessionId: $sessionId, reviews: $reviews) {
      success
      error
      session {
        id
        proposals {
          id
          approved
          rejected
          selectedCustomerId
          error
        }
      }
    }
  }
`

const APPLY_IMPORT_PROPOSALS = gql`
  mutation ApplyImportProposals($sessionId: String!, $autoCreateProducts: Boolean) {
    applyImportProposals(sessionId: $sessionId, autoCreateProducts: $autoCreateProducts) {
      success
      error
      createdContracts {
        id
        name
        customer {
          name
        }
      }
      errorsByProposal
    }
  }
`

const CANCEL_IMPORT_SESSION = gql`
  mutation CancelImportSession($sessionId: String!) {
    cancelImportSession(sessionId: $sessionId) {
      success
      error
    }
  }
`

const SEARCH_CUSTOMERS = gql`
  query SearchCustomers($search: String!, $isActive: Boolean) {
    customers(search: $search, isActive: $isActive, pageSize: 20) {
      items {
        id
        name
        address
      }
    }
  }
`

interface CustomerSearchResult {
  id: number
  name: string
  address: { city?: string } | null
}

interface MatchAlternative {
  customerId: number
  customerName: string
  customerCity: string | null
  confidence: number
}

interface MatchResult {
  status: 'matched' | 'review' | 'not_found'
  customerId: number | null
  customerName: string | null
  customerCity: string | null
  confidence: number
  originalName: string
  alternatives: MatchAlternative[]
}

interface LineItem {
  itemName: string
  monthlyRate: number
  productId: number | null
  productName: string | null
}

interface Proposal {
  id: string
  customerNumber: string
  customerName: string
  salesOrderNumber: string
  contractNumber: string
  startDate: string | null
  endDate: string | null
  invoicingInstructions: string
  matchResult: MatchResult | null
  selectedCustomerId: number | null
  items: LineItem[]
  discountAmount: number
  totalMonthlyRate: number
  approved: boolean
  rejected: boolean
  error: string | null
  needsReview: boolean
  existingContractId: number | null
}

interface ImportSummary {
  totalProposals: number
  autoMatched: number
  needsReview: number
  notFound: number
  totalItems: number
  alreadyImported: number
}

interface ImportSession {
  id: string
  proposals: Proposal[]
  summary: ImportSummary
  parserErrors: string[]
}

interface LocalApproval {
  approved: boolean
  selectedCustomerId: number | null
  selectedCustomerName?: string
  selectedCustomerCity?: string | null
}

export function ContractImport() {
  const { t } = useTranslation()
  const [session, setSession] = useState<ImportSession | null>(null)
  const [expandedProposals, setExpandedProposals] = useState<Set<string>>(new Set())
  const [localApprovals, setLocalApprovals] = useState<Map<string, LocalApproval>>(new Map())
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [applyResult, setApplyResult] = useState<{ success: boolean; contracts: Array<{ id: string; name: string; customer: { name: string } }> } | null>(null)

  // Customer search state
  const [searchingProposalId, setSearchingProposalId] = useState<string | null>(null)
  const [customerSearch, setCustomerSearch] = useState('')
  const [searchResults, setSearchResults] = useState<CustomerSearchResult[]>([])
  const searchInputRef = useRef<HTMLInputElement>(null)

  const [uploadImport, { loading: uploading }] = useMutation(UPLOAD_CONTRACT_IMPORT)
  const [reviewProposals, { loading: reviewing }] = useMutation(REVIEW_IMPORT_PROPOSALS)
  const [applyProposals, { loading: applying }] = useMutation(APPLY_IMPORT_PROPOSALS)
  const [cancelSession] = useMutation(CANCEL_IMPORT_SESSION)
  const [searchCustomers, { loading: searchingCustomers }] = useLazyQuery(SEARCH_CUSTOMERS)

  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.name.endsWith('.xlsx')) {
      setUploadError(t('import.invalidFileType'))
      return
    }

    setUploadError(null)
    setApplyResult(null)

    // Read file as base64
    const reader = new FileReader()
    reader.onload = async (e) => {
      const base64 = (e.target?.result as string)?.split(',')[1]
      if (!base64) {
        setUploadError(t('import.readError'))
        return
      }

      try {
        const result = await uploadImport({
          variables: {
            fileContent: base64,
            filename: file.name,
            autoApproveThreshold: 0.9,
          },
        })

        if (result.data?.uploadContractImport?.success) {
          setSession(result.data.uploadContractImport.session)
          // Pre-approve high-confidence matches
          const approvals = new Map<string, LocalApproval>()
          result.data.uploadContractImport.session.proposals.forEach((p: Proposal) => {
            if (p.matchResult?.status === 'matched') {
              approvals.set(p.id, {
                approved: true,
                selectedCustomerId: p.matchResult.customerId,
                selectedCustomerName: p.matchResult.customerName || undefined,
                selectedCustomerCity: p.matchResult.customerCity,
              })
            }
          })
          setLocalApprovals(approvals)
        } else {
          setUploadError(result.data?.uploadContractImport?.error || t('import.uploadFailed'))
        }
      } catch (err) {
        setUploadError(t('import.uploadFailed'))
      }
    }
    reader.readAsDataURL(file)

    // Reset the input
    event.target.value = ''
  }, [t, uploadImport])

  const toggleExpanded = (id: string) => {
    setExpandedProposals(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleApproval = (proposalId: string, approved: boolean, customerId: number | null, customerName?: string, customerCity?: string | null) => {
    setLocalApprovals(prev => {
      const next = new Map(prev)
      next.set(proposalId, {
        approved,
        selectedCustomerId: customerId,
        selectedCustomerName: customerName,
        selectedCustomerCity: customerCity,
      })
      return next
    })
  }

  const handleSelectCustomer = (proposalId: string, customer: { id: number, name: string, city?: string | null }) => {
    setLocalApprovals(prev => {
      const next = new Map(prev)
      next.set(proposalId, {
        approved: true,
        selectedCustomerId: customer.id,
        selectedCustomerName: customer.name,
        selectedCustomerCity: customer.city,
      })
      return next
    })
    // Close search
    setSearchingProposalId(null)
    setCustomerSearch('')
    setSearchResults([])
  }

  // Handle customer search
  useEffect(() => {
    if (searchingProposalId && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [searchingProposalId])

  useEffect(() => {
    if (!customerSearch || customerSearch.length < 2) {
      setSearchResults([])
      return
    }

    const timeoutId = setTimeout(async () => {
      const result = await searchCustomers({
        variables: { search: customerSearch, isActive: null }
      })
      if (result.data?.customers?.items) {
        setSearchResults(result.data.customers.items)
      }
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [customerSearch, searchCustomers])

  const openCustomerSearch = (proposalId: string) => {
    setSearchingProposalId(proposalId)
    setCustomerSearch('')
    setSearchResults([])
  }

  const closeCustomerSearch = () => {
    setSearchingProposalId(null)
    setCustomerSearch('')
    setSearchResults([])
  }

  const getCustomerCity = (address: { city?: string } | null): string | null => {
    return address?.city || null
  }

  const handleApplyImport = async () => {
    if (!session) return

    // First, submit all reviews
    const reviews = Array.from(localApprovals.entries()).map(([proposalId, { approved, selectedCustomerId }]) => ({
      proposalId,
      approved,
      selectedCustomerId: selectedCustomerId?.toString() || null,
    }))

    try {
      await reviewProposals({
        variables: {
          sessionId: session.id,
          reviews,
        },
      })

      // Then apply the proposals
      const result = await applyProposals({
        variables: {
          sessionId: session.id,
          autoCreateProducts: true,
        },
      })

      if (result.data?.applyImportProposals?.success) {
        setApplyResult({
          success: true,
          contracts: result.data.applyImportProposals.createdContracts,
        })
        setSession(null)
        setLocalApprovals(new Map())
      } else {
        setUploadError(result.data?.applyImportProposals?.error || t('import.applyFailed'))
      }
    } catch {
      setUploadError(t('import.applyFailed'))
    }
  }

  const handleCancel = async () => {
    if (!session) return
    await cancelSession({ variables: { sessionId: session.id } })
    setSession(null)
    setLocalApprovals(new Map())
    setUploadError(null)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'matched':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'review':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      case 'not_found':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  const getApprovalStatus = (proposal: Proposal) => {
    const local = localApprovals.get(proposal.id)
    if (local) {
      return local.approved ? 'approved' : 'rejected'
    }
    return 'pending'
  }

  const approvedCount = Array.from(localApprovals.values()).filter(v => v.approved).length
  const pendingReviewCount = session?.proposals.filter(p =>
    p.matchResult?.status === 'review' && !localApprovals.has(p.id)
  ).length || 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-medium">{t('import.title')}</h2>
          <p className="mt-1 text-sm text-gray-500">{t('import.description')}</p>
        </div>
      </div>

      {/* Success Result */}
      {applyResult?.success && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            <span className="font-medium text-green-800">
              {t('import.importSuccess', { count: applyResult.contracts.length })}
            </span>
          </div>
          <ul className="mt-2 ml-7 space-y-1 text-sm text-green-700">
            {applyResult.contracts.map(c => (
              <li key={c.id}>{c.name} ({c.customer.name})</li>
            ))}
          </ul>
        </div>
      )}

      {/* Error Display */}
      {uploadError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-500" />
            <span className="text-red-800">{uploadError}</span>
          </div>
        </div>
      )}

      {/* Upload Section */}
      {!session && (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-8">
          <div className="text-center">
            <FileSpreadsheet className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4">
              <label className="cursor-pointer">
                <span className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                  {uploading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {t('import.uploading')}
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      {t('import.selectFile')}
                    </>
                  )}
                </span>
                <input
                  type="file"
                  accept=".xlsx"
                  onChange={handleFileSelect}
                  disabled={uploading}
                  className="hidden"
                />
              </label>
            </div>
            <p className="mt-2 text-xs text-gray-500">{t('import.fileHint')}</p>
          </div>
        </div>
      )}

      {/* Session Display */}
      {session && (
        <div className="space-y-4">
          {/* Summary */}
          <div className="rounded-lg border bg-white p-4">
            <h3 className="font-medium">{t('import.summary')}</h3>
            <div className="mt-2 grid grid-cols-2 gap-4 sm:grid-cols-5">
              <div>
                <div className="text-2xl font-semibold">{session.summary.totalProposals}</div>
                <div className="text-sm text-gray-500">{t('import.totalProposals')}</div>
              </div>
              <div>
                <div className="text-2xl font-semibold text-green-600">{session.summary.autoMatched}</div>
                <div className="text-sm text-gray-500">{t('import.autoMatched')}</div>
              </div>
              <div>
                <div className="text-2xl font-semibold text-yellow-600">{session.summary.needsReview}</div>
                <div className="text-sm text-gray-500">{t('import.needsReview')}</div>
              </div>
              <div>
                <div className="text-2xl font-semibold text-red-600">{session.summary.notFound}</div>
                <div className="text-sm text-gray-500">{t('import.notFound')}</div>
              </div>
              {session.summary.alreadyImported > 0 && (
                <div>
                  <div className="text-2xl font-semibold text-gray-400">{session.summary.alreadyImported}</div>
                  <div className="text-sm text-gray-500">{t('import.alreadyImported')}</div>
                </div>
              )}
            </div>
          </div>

          {/* Parser Errors */}
          {session.parserErrors.length > 0 && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
              <h4 className="font-medium text-yellow-800">{t('import.parserErrors')}</h4>
              <ul className="mt-2 space-y-1 text-sm text-yellow-700">
                {session.parserErrors.map((error, i) => (
                  <li key={i}>{error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Proposals List */}
          <div className="rounded-lg border bg-white">
            <div className="border-b px-4 py-3">
              <h3 className="font-medium">{t('import.proposals')}</h3>
              <p className="text-sm text-gray-500">
                {t('import.approvedCount', { approved: approvedCount, total: session.proposals.length })}
                {pendingReviewCount > 0 && (
                  <span className="ml-2 text-yellow-600">
                    ({t('import.pendingReview', { count: pendingReviewCount })})
                  </span>
                )}
              </p>
            </div>

            <div className="divide-y">
              {session.proposals.map(proposal => {
                const isExpanded = expandedProposals.has(proposal.id)
                const approvalStatus = getApprovalStatus(proposal)
                const local = localApprovals.get(proposal.id)
                const isAlreadyImported = proposal.existingContractId !== null

                return (
                  <div key={proposal.id} className={`p-4 ${isAlreadyImported ? 'bg-gray-100 opacity-60' : ''}`}>
                    {/* Proposal Header */}
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => toggleExpanded(proposal.id)}
                        className="flex-shrink-0"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronRight className="h-5 w-5 text-gray-400" />
                        )}
                      </button>

                      {isAlreadyImported ? (
                        <CheckCircle className="h-5 w-5 text-gray-400" />
                      ) : (
                        proposal.matchResult && getStatusIcon(proposal.matchResult.status)
                      )}

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className={`font-medium truncate ${isAlreadyImported ? 'text-gray-500' : ''}`}>{proposal.customerName}</span>
                          <span className="text-sm text-gray-500">({proposal.customerNumber})</span>
                          {isAlreadyImported && (
                            <span className="inline-flex items-center rounded-full bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-600">
                              {t('import.alreadyImportedBadge')}
                            </span>
                          )}
                        </div>
                        <div className="text-sm text-gray-500">
                          <span className="font-medium text-gray-700">{t('import.salesOrder')}:</span> {proposal.salesOrderNumber}
                          {proposal.contractNumber && (
                            <>
                              <span className="mx-2">|</span>
                              <span className="font-medium text-gray-700">{t('import.contractNumber')}:</span> {proposal.contractNumber}
                            </>
                          )}
                          <span className="mx-2">|</span>
                          {proposal.items.length} {t('import.items')}
                          {proposal.discountAmount !== 0 && (
                            <span className="ml-2 text-red-600">
                              {t('import.discount')}: {proposal.discountAmount.toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {!isAlreadyImported && proposal.matchResult && proposal.matchResult.confidence > 0 && (
                          <span className={`text-sm ${
                            proposal.matchResult.status === 'matched' ? 'text-green-600' : 'text-yellow-600'
                          }`}>
                            {Math.round(proposal.matchResult.confidence * 100)}%
                          </span>
                        )}

                        {/* Import Toggle - disabled for already imported */}
                        {isAlreadyImported ? (
                          <span className="text-sm text-gray-400 italic">{t('import.existsInSystem')}</span>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className={`text-xs ${approvalStatus !== 'approved' ? 'font-medium text-gray-700' : 'text-gray-400'}`}>
                              {t('import.skip')}
                            </span>
                            <button
                              onClick={() => {
                                const newApproved = approvalStatus !== 'approved'
                                const customerId = local?.selectedCustomerId || proposal.matchResult?.customerId || null
                                const customerName = local?.selectedCustomerName || proposal.matchResult?.customerName || undefined
                                const customerCity = local?.selectedCustomerCity !== undefined ? local.selectedCustomerCity : proposal.matchResult?.customerCity
                                handleApproval(proposal.id, newApproved, customerId, customerName, customerCity)
                              }}
                              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                approvalStatus === 'approved' ? 'bg-green-500' : 'bg-gray-300'
                              }`}
                            >
                              <span
                                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                  approvalStatus === 'approved' ? 'translate-x-6' : 'translate-x-1'
                                }`}
                              />
                            </button>
                            <span className={`text-xs ${approvalStatus === 'approved' ? 'font-medium text-green-700' : 'text-gray-400'}`}>
                              {t('import.import')}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Expanded Details */}
                    {isExpanded && (
                      <div className="mt-4 ml-10 space-y-4">
                        {/* Match Info */}
                        <div className="rounded bg-gray-50 p-3">
                          <div className="flex items-center justify-between">
                            <h4 className="text-sm font-medium">{t('import.matchedTo')}</h4>
                            <button
                              onClick={() => openCustomerSearch(proposal.id)}
                              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800"
                            >
                              <Search className="h-3 w-3" />
                              {t('import.searchCustomer')}
                            </button>
                          </div>

                          {/* Selected/Matched Customer Display */}
                          {(local?.selectedCustomerId || proposal.matchResult?.customerId) ? (
                            <div className="mt-2 flex items-center gap-2 rounded border border-green-200 bg-green-50 px-3 py-2">
                              <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
                              <div>
                                <span className="font-medium">
                                  {local?.selectedCustomerName || proposal.matchResult?.customerName}
                                </span>
                                {(local?.selectedCustomerCity || proposal.matchResult?.customerCity) && (
                                  <span className="ml-2 text-gray-600">
                                    ({local?.selectedCustomerCity || proposal.matchResult?.customerCity})
                                  </span>
                                )}
                                {proposal.matchResult && proposal.matchResult.confidence > 0 && !local?.selectedCustomerId && (
                                  <span className="ml-2 text-sm text-gray-500">
                                    - {Math.round(proposal.matchResult.confidence * 100)}% {t('import.confidence')}
                                  </span>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div className="mt-2 flex items-center gap-2 rounded border border-red-200 bg-red-50 px-3 py-2">
                              <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
                              <span className="text-red-700">{t('import.noCustomerSelected')}</span>
                            </div>
                          )}

                          {/* Customer Search */}
                          {searchingProposalId === proposal.id && (
                            <div className="mt-3 border-t pt-3">
                              <div className="relative">
                                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                                <input
                                  ref={searchInputRef}
                                  type="text"
                                  value={customerSearch}
                                  onChange={(e) => setCustomerSearch(e.target.value)}
                                  placeholder={t('import.searchCustomerPlaceholder')}
                                  className="w-full rounded-md border py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                                />
                                {searchingCustomers && (
                                  <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-gray-400" />
                                )}
                              </div>

                              {/* Search Results */}
                              {searchResults.length > 0 && (
                                <div className="mt-2 max-h-48 overflow-y-auto rounded border bg-white">
                                  {searchResults.map(customer => (
                                    <button
                                      key={customer.id}
                                      onClick={() => handleSelectCustomer(proposal.id, {
                                        id: customer.id,
                                        name: customer.name,
                                        city: getCustomerCity(customer.address),
                                      })}
                                      className="block w-full px-3 py-2 text-left text-sm hover:bg-gray-100"
                                    >
                                      <span className="font-medium">{customer.name}</span>
                                      {customer.address?.city && (
                                        <span className="ml-2 text-gray-500">({customer.address.city})</span>
                                      )}
                                    </button>
                                  ))}
                                </div>
                              )}

                              {customerSearch.length >= 2 && searchResults.length === 0 && !searchingCustomers && (
                                <p className="mt-2 text-sm text-gray-500">{t('import.noCustomersFound')}</p>
                              )}

                              <button
                                onClick={closeCustomerSearch}
                                className="mt-2 text-xs text-gray-500 hover:text-gray-700"
                              >
                                {t('common.cancel')}
                              </button>
                            </div>
                          )}

                          {/* Alternatives */}
                          {proposal.matchResult && proposal.matchResult.alternatives.length > 0 && searchingProposalId !== proposal.id && (
                            <div className="mt-3 border-t pt-3">
                              <h5 className="text-xs font-medium text-gray-500">{t('import.alternatives')}</h5>
                              <div className="mt-1 space-y-1">
                                {proposal.matchResult.alternatives.map(alt => (
                                  <button
                                    key={alt.customerId}
                                    onClick={() => handleSelectCustomer(proposal.id, {
                                      id: alt.customerId,
                                      name: alt.customerName,
                                      city: alt.customerCity,
                                    })}
                                    className={`block w-full text-left rounded px-2 py-1 text-sm hover:bg-gray-100 ${
                                      local?.selectedCustomerId === alt.customerId ? 'bg-blue-50 text-blue-700' : ''
                                    }`}
                                  >
                                    <span>{alt.customerName}</span>
                                    {alt.customerCity && (
                                      <span className="ml-1 text-gray-500">({alt.customerCity})</span>
                                    )}
                                    <span className="ml-2 text-gray-400">
                                      {Math.round(alt.confidence * 100)}%
                                    </span>
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Line Items */}
                        <div>
                          <h4 className="text-sm font-medium">{t('import.lineItems')}</h4>
                          <table className="mt-2 w-full text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-2 py-1 text-left">{t('import.item')}</th>
                                <th className="px-2 py-1 text-right">{t('import.monthlyRate')}</th>
                                <th className="px-2 py-1 text-left">{t('import.product')}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {proposal.items.map((item, i) => (
                                <tr key={i} className="border-t">
                                  <td className="px-2 py-1">{item.itemName}</td>
                                  <td className="px-2 py-1 text-right">{item.monthlyRate.toFixed(2)}</td>
                                  <td className="px-2 py-1">
                                    {item.productName || (
                                      <span className="text-yellow-600">{t('import.newProduct')}</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                              {proposal.discountAmount !== 0 && (
                                <tr className="border-t text-red-600">
                                  <td className="px-2 py-1">{t('import.discount')}</td>
                                  <td className="px-2 py-1 text-right">{proposal.discountAmount.toFixed(2)}</td>
                                  <td className="px-2 py-1">-</td>
                                </tr>
                              )}
                              <tr className="border-t font-medium">
                                <td className="px-2 py-1">{t('import.total')}</td>
                                <td className="px-2 py-1 text-right">{proposal.totalMonthlyRate.toFixed(2)}</td>
                                <td className="px-2 py-1">-</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        {/* Notes */}
                        {proposal.invoicingInstructions && (
                          <div>
                            <h4 className="text-sm font-medium">{t('import.notes')}</h4>
                            <p className="mt-1 text-sm text-gray-600">{proposal.invoicingInstructions}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-4">
            <button
              onClick={handleCancel}
              className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleApplyImport}
              disabled={applying || reviewing || approvedCount === 0}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {(applying || reviewing) && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('import.applyImport', { count: approvedCount })}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
