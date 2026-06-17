import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  ArrowLeft,
  Loader2,
  Download,
  Send,
  Trash2,
  AlertCircle,
  FileText,
  Lock,
  RefreshCcw,
  Copy,
  CheckCircle2,
  Save,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import { getToken } from '@/lib/auth'
import { SendOfferDialog } from './SendOfferDialog'

// ----------------------------------------------------------------------------
// GraphQL
// ----------------------------------------------------------------------------

const OFFER_QUERY = gql`
  query Offer($id: Int!) {
    offer(id: $id) {
      id
      offerNumber
      contractId
      contractName
      customerId
      customerName
      offerDate
      validUntil
      billingDate
      periodStart
      periodEnd
      totalNet
      taxRate
      taxAmount
      totalGross
      status
      isLocked
      createdAt
      lineItemsSnapshot
      pdfUrl
      vatSentence
      customerBillingEmails
      emailSentAt
      emailSentTo
      emailMessageId
      freeTextAfterItems
      freeTextBeforeTerms
      minimumTermMonths
      noticePeriodMonths
      clonedFromId
    }
  }
`

const UPDATE_OFFER = gql`
  mutation UpdateOffer($id: Int!, $input: UpdateOfferInput!) {
    updateOffer(id: $id, input: $input) {
      success
      error
      isLockedError
      offer {
        id
        status
        isLocked
      }
    }
  }
`

const RECREATE_OFFER = gql`
  mutation RecreateOfferFromContract($id: Int!) {
    recreateOfferFromContract(id: $id) {
      success
      error
      isLockedError
    }
  }
`

const FINALIZE_OFFER = gql`
  mutation FinalizeOffer($id: Int!) {
    finalizeOffer(id: $id) {
      success
      error
      isLockedError
    }
  }
`

const CLONE_OFFER = gql`
  mutation CloneOfferToDraft($id: Int!) {
    cloneOfferToDraft(id: $id) {
      success
      error
      offer {
        id
      }
    }
  }
`

const DELETE_OFFER = gql`
  mutation DeleteOffer($id: Int!) {
    deleteOffer(id: $id) {
      success
      error
    }
  }
`

interface LineItem {
  item_id: number
  product_name: string
  description: string
  quantity: number
  unit_price: string
  amount: string
  is_prorated: boolean
  prorate_factor: string | null
  is_one_off: boolean
}

// ----------------------------------------------------------------------------
// Sub-components
// ----------------------------------------------------------------------------

/** Markdown textarea + live preview, side by side. Read-only when locked
 * (renders as static HTML preview). */
function MarkdownField({
  label,
  hint,
  value,
  onChange,
  onBlur,
  readOnly,
  testid,
}: {
  label: string
  hint: string
  value: string
  onChange: (v: string) => void
  onBlur?: () => void
  readOnly: boolean
  testid?: string
}) {
  return (
    <div className="rounded-lg border bg-white p-4 space-y-2">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-medium text-gray-700">{label}</h3>
        {!readOnly && <span className="text-xs text-gray-400">{hint}</span>}
      </div>
      {readOnly ? (
        <div className="prose prose-sm max-w-none">
          {value.trim() ? (
            <ReactMarkdown>{value}</ReactMarkdown>
          ) : (
            <span className="text-xs italic text-gray-400">—</span>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <textarea
            className="min-h-[140px] w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono focus:border-blue-500 focus:outline-none"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            data-testid={testid}
          />
          <div className="prose prose-sm max-w-none rounded border border-dashed border-gray-200 bg-gray-50 px-3 py-2">
            {value.trim() ? (
              <ReactMarkdown>{value}</ReactMarkdown>
            ) : (
              <span className="text-xs italic text-gray-400">
                Live preview
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ----------------------------------------------------------------------------
// Main
// ----------------------------------------------------------------------------

export function OfferDetail() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showSendDialog, setShowSendDialog] = useState(false)
  const [showRecreateDialog, setShowRecreateDialog] = useState(false)
  const [toast, setToast] = useState<
    { kind: 'success' | 'error'; text: string } | null
  >(null)

  const { data, loading, error, refetch } = useQuery(OFFER_QUERY, {
    variables: { id: parseInt(id!) },
    skip: !id,
  })

  const [updateOffer, { loading: saving }] = useMutation(UPDATE_OFFER)
  const [recreateOffer, { loading: recreating }] = useMutation(RECREATE_OFFER)
  const [finalizeOffer, { loading: finalizing }] = useMutation(FINALIZE_OFFER)
  const [cloneOffer, { loading: cloning }] = useMutation(CLONE_OFFER)
  const [deleteOffer, { loading: deleting }] = useMutation(DELETE_OFFER)

  const offer = data?.offer

  // ---------- Local editing state (draft only) ----------
  const [freeTextAfter, setFreeTextAfter] = useState('')
  const [freeTextBefore, setFreeTextBefore] = useState('')
  const [validUntil, setValidUntil] = useState('')
  const [minimumTerm, setMinimumTerm] = useState('')
  const [noticePeriod, setNoticePeriod] = useState('')
  const [isDirty, setIsDirty] = useState(false)
  // Bumped after each successful save so the PDF preview re-fetches even
  // though `pdfUrl` is the same string (backend writes to the same path).
  const [pdfReloadToken, setPdfReloadToken] = useState(0)

  // Reset local state ONLY when the offer ID changes (i.e. user navigates
  // to a different offer). Refetches of the SAME offer must not blow
  // away in-progress edits — that was the bug behind "save doesn't stick":
  // typing field A, blurring, then typing in field B; the refetch after
  // A's save would clobber B's draft state with the stale server value.
  useEffect(() => {
    if (!offer) return
    setFreeTextAfter(offer.freeTextAfterItems || '')
    setFreeTextBefore(offer.freeTextBeforeTerms || '')
    setValidUntil(offer.validUntil || '')
    setMinimumTerm(
      offer.minimumTermMonths != null ? String(offer.minimumTermMonths) : '',
    )
    setNoticePeriod(
      offer.noticePeriodMonths != null ? String(offer.noticePeriodMonths) : '',
    )
    setIsDirty(false)
  }, [offer?.id])

  // ---------- PDF blob fetch ----------
  // Re-runs when `pdfReloadToken` changes (after each save) so the
  // preview reflects the server-side regenerated PDF. Without this, the
  // iframe keeps showing the pre-save PDF because `offer.pdfUrl` is the
  // same string after re-save (same file path, contents replaced).
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!offer?.pdfUrl) return
    const token = getToken()
    fetch(`/api/offers/${offer.id}/pdf/?t=${pdfReloadToken}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((blob) => setPdfBlobUrl(URL.createObjectURL(blob)))
      .catch(() => setPdfBlobUrl(null))
    return () => {
      setPdfBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return null
      })
    }
  }, [offer?.id, offer?.pdfUrl, pdfReloadToken])

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return
    const handle = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(handle)
  }, [toast])

  // ---------- Memoized derived values (must come before any return) ----------
  const lineItems: LineItem[] = useMemo(
    () => (offer?.lineItemsSnapshot as LineItem[] | null) || [],
    [offer?.lineItemsSnapshot],
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !offer) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/offers')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('common.back')}
        </Button>
        <div className="py-20 text-center text-gray-500">
          <AlertCircle className="mx-auto mb-2 h-8 w-8" />
          {t('offers.detail.notFound')}
        </div>
      </div>
    )
  }

  const today = new Date().toISOString().slice(0, 10)
  const isExpired = offer.validUntil && offer.validUntil < today
  const isDraft = offer.status === 'draft'
  const isLocked = !!offer.isLocked
  const isFinalized = offer.status === 'finalized'
  const isSent = offer.status === 'sent'

  // ----------------------------------------------------------------
  // Mutation handlers
  // ----------------------------------------------------------------

  const buildUpdateInput = () => {
    const input: Record<string, unknown> = {}
    input.freeTextAfterItems = freeTextAfter
    input.freeTextBeforeTerms = freeTextBefore
    input.validUntil = validUntil || null
    input.minimumTermMonths =
      minimumTerm.trim() === '' ? null : parseInt(minimumTerm, 10)
    input.noticePeriodMonths =
      noticePeriod.trim() === '' ? null : parseInt(noticePeriod, 10)
    return input
  }

  const saveAll = async () => {
    if (!isDraft) return
    if (!isDirty) return
    const result = await updateOffer({
      variables: { id: offer.id, input: buildUpdateInput() },
    })
    const payload = result.data?.updateOffer
    if (payload?.success) {
      setToast({ kind: 'success', text: t('offers.saved') })
      setIsDirty(false)
      // Force the PDF preview to re-fetch even though the URL string
      // didn't change — server overwrote the same file path.
      setPdfReloadToken((n) => n + 1)
      refetch()
    } else {
      setToast({
        kind: 'error',
        text: payload?.error || t('offers.saveFailed'),
      })
    }
  }

  const handleRecreate = async () => {
    setShowRecreateDialog(false)
    const result = await recreateOffer({ variables: { id: offer.id } })
    const payload = result.data?.recreateOfferFromContract
    if (payload?.success) {
      setToast({ kind: 'success', text: t('offers.recreated') })
      setPdfReloadToken((n) => n + 1)
      refetch()
    } else {
      setToast({
        kind: 'error',
        text: payload?.error || t('offers.recreateFailed'),
      })
    }
  }

  const handleFinalize = async () => {
    if (!window.confirm(t('offers.finalizeConfirm'))) return
    const result = await finalizeOffer({ variables: { id: offer.id } })
    const payload = result.data?.finalizeOffer
    if (payload?.success) {
      setToast({ kind: 'success', text: t('offers.finalized') })
      setPdfReloadToken((n) => n + 1)
      refetch()
    } else {
      setToast({
        kind: 'error',
        text: payload?.error || t('offers.finalizeFailed'),
      })
    }
  }

  const handleClone = async () => {
    const result = await cloneOffer({ variables: { id: offer.id } })
    const payload = result.data?.cloneOfferToDraft
    if (payload?.success && payload.offer) {
      setToast({ kind: 'success', text: t('offers.cloned') })
      navigate(`/offers/${payload.offer.id}`)
    } else {
      setToast({
        kind: 'error',
        text: payload?.error || t('offers.cloneFailed'),
      })
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(t('offers.detail.deleteConfirm'))) return
    const result = await deleteOffer({ variables: { id: offer.id } })
    if (result.data?.deleteOffer?.success) {
      navigate('/offers')
    }
  }

  // ----------------------------------------------------------------
  // Status badge + labels (lifecycle: draft → sent | finalized)
  // ----------------------------------------------------------------

  const statusVariants: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-blue-100 text-blue-700',
    finalized: 'bg-purple-100 text-purple-700',
    // Legacy values — keep readable but no transition path.
    accepted: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-500',
  }

  const statusLabels: Record<string, string> = {
    draft: t('offers.statusDraft'),
    sent: t('offers.statusSent'),
    finalized: t('offers.statusFinalized', { defaultValue: 'Finalized' }),
    accepted: t('offers.statusAccepted'),
    rejected: t('offers.statusRejected'),
    cancelled: t('offers.statusCancelled'),
  }

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div
          className={cn(
            'fixed right-4 top-4 z-50 rounded-lg px-4 py-3 text-sm font-medium shadow-lg',
            toast.kind === 'success'
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800',
          )}
        >
          {toast.text}
        </div>
      )}

      {/* Back + Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/offers')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common.back')}
          </Button>
          <div>
            <h1 className="flex items-center gap-3 text-2xl font-semibold">
              {t('offers.detail.title')} {offer.offerNumber}
              <span
                className={cn(
                  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                  statusVariants[offer.status] ||
                    'bg-gray-100 text-gray-700',
                )}
              >
                {statusLabels[offer.status] || offer.status}
              </span>
              {offer.clonedFromId && (
                <Badge variant="outline" className="text-xs">
                  <Copy className="mr-1 h-3 w-3" />
                  {t('offers.clonedFromBadge', {
                    defaultValue: 'Cloned',
                  })}
                </Badge>
              )}
              {isExpired && (isDraft || isSent) && (
                <Badge variant="destructive" className="text-xs">
                  <AlertCircle className="mr-1 h-3 w-3" />
                  {t('offers.statusExpired')}
                </Badge>
              )}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {pdfBlobUrl && (
            <Button variant="outline" size="sm" asChild>
              <a
                href={pdfBlobUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Download className="mr-2 h-4 w-4" />
                PDF
              </a>
            </Button>
          )}

          {/* Draft actions */}
          {isDraft && (
            <>
              {isDirty && !saving && (
                <span className="text-xs italic text-amber-600">
                  {t('offers.unsavedChanges', {
                    defaultValue: 'Ungespeicherte Änderungen',
                  })}
                </span>
              )}
              <Button
                size="sm"
                variant={isDirty ? 'default' : 'outline'}
                onClick={saveAll}
                disabled={saving || !isDirty}
                data-testid="offer-save"
              >
                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Save className="mr-2 h-4 w-4" />
                {t('common.save')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowRecreateDialog(true)}
                disabled={recreating}
                data-testid="offer-recreate"
              >
                {recreating && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                <RefreshCcw className="mr-2 h-4 w-4" />
                {t('offers.recreateFromContract')}
              </Button>
              {offer.pdfUrl && (
                <Button size="sm" onClick={() => setShowSendDialog(true)}>
                  <Send className="mr-2 h-4 w-4" />
                  {t('offers.detail.send')}
                </Button>
              )}
              <Button
                size="sm"
                variant="default"
                onClick={handleFinalize}
                disabled={finalizing}
                data-testid="offer-finalize"
              >
                {finalizing && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                <CheckCircle2 className="mr-2 h-4 w-4" />
                {t('offers.finalize')}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleDelete}
                disabled={deleting}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {t('common.delete')}
              </Button>
            </>
          )}

          {/* Locked actions */}
          {isLocked && (
            <Button
              size="sm"
              variant="default"
              onClick={handleClone}
              disabled={cloning}
              data-testid="offer-clone"
            >
              {cloning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              <Copy className="mr-2 h-4 w-4" />
              {t('offers.copyToEdit')}
            </Button>
          )}
        </div>
      </div>

      {/* Locked banner */}
      {isLocked && (
        <div
          className="rounded-lg border border-purple-200 bg-purple-50 p-4 text-purple-900"
          data-testid="offer-locked-banner"
        >
          <div className="flex items-start gap-3">
            <Lock className="mt-0.5 h-5 w-5 flex-shrink-0" />
            <div className="flex-1">
              <p className="font-semibold">
                {t('offers.lockedBannerTitle')}
              </p>
              <p className="mt-1 text-sm">
                {isSent
                  ? t('offers.lockedBannerSent', {
                      date: offer.emailSentAt
                        ? formatDate(offer.emailSentAt)
                        : '—',
                      recipients: (offer.emailSentTo || []).join(', '),
                    })
                  : isFinalized
                  ? t('offers.lockedBannerFinalized', {
                      date: formatDate(offer.createdAt),
                    })
                  : statusLabels[offer.status]}
              </p>
              <p className="mt-2 text-xs">{t('offers.lockedBannerHint')}</p>
            </div>
          </div>
        </div>
      )}

      {/* Metadata + PDF Preview */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left: Metadata + editors */}
        <div className="space-y-4">
          <div className="space-y-3 rounded-lg border bg-white p-4">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-gray-500">
                {t('offers.detail.offerDate')}
              </span>
              <span>{formatDate(offer.offerDate)}</span>

              <span className="text-gray-500">
                {t('offers.detail.validUntil')}
              </span>
              {isDraft ? (
                <Input
                  type="date"
                  className="h-7 text-sm"
                  value={validUntil}
                  onChange={(e) => { setValidUntil(e.target.value); setIsDirty(true) }}
                  onBlur={saveAll}
                  data-testid="offer-valid-until"
                />
              ) : (
                <span
                  className={cn(
                    isExpired && 'font-medium text-red-600',
                  )}
                >
                  {offer.validUntil ? formatDate(offer.validUntil) : '—'}
                </span>
              )}

              <span className="text-gray-500">
                {t('offers.detail.customer')}
              </span>
              <span>
                {offer.customerId ? (
                  <Link
                    to={`/customers/${offer.customerId}`}
                    className="text-primary hover:underline"
                  >
                    {offer.customerName}
                  </Link>
                ) : (
                  offer.customerName
                )}
              </span>

              <span className="text-gray-500">
                {t('offers.detail.contract')}
              </span>
              <span>
                {offer.contractId ? (
                  <Link
                    to={`/contracts/${offer.contractId}`}
                    className="text-primary hover:underline"
                  >
                    {offer.contractName}
                  </Link>
                ) : (
                  offer.contractName
                )}
              </span>

              <span className="text-gray-500">
                {t('offers.detail.period')}
              </span>
              <span>
                {formatDate(offer.periodStart)} –{' '}
                {formatDate(offer.periodEnd)}
              </span>

              <span className="text-gray-500">
                {t('offers.detail.billingDate')}
              </span>
              <span>{formatDate(offer.billingDate)}</span>

              <span className="text-gray-500">
                {t('offers.minimumTerm')}
              </span>
              {isDraft ? (
                <Input
                  type="number"
                  min="0"
                  step="1"
                  className="h-7 text-sm"
                  value={minimumTerm}
                  onChange={(e) => { setMinimumTerm(e.target.value); setIsDirty(true) }}
                  onBlur={saveAll}
                  data-testid="offer-min-term"
                />
              ) : (
                <span>
                  {offer.minimumTermMonths != null
                    ? offer.minimumTermMonths
                    : '—'}
                </span>
              )}

              <span className="text-gray-500">
                {t('offers.noticePeriod')}
              </span>
              {isDraft ? (
                <Input
                  type="number"
                  min="0"
                  step="1"
                  className="h-7 text-sm"
                  value={noticePeriod}
                  onChange={(e) => { setNoticePeriod(e.target.value); setIsDirty(true) }}
                  onBlur={saveAll}
                  data-testid="offer-notice-period"
                />
              ) : (
                <span>
                  {offer.noticePeriodMonths != null
                    ? offer.noticePeriodMonths
                    : '—'}
                </span>
              )}
            </div>
          </div>

          {/* Free-text editors */}
          <MarkdownField
            label={t('offers.freeTextAfterItems')}
            hint={t('offers.freeTextHint')}
            value={freeTextAfter}
            onChange={(v) => { setFreeTextAfter(v); setIsDirty(true) }}
            onBlur={saveAll}
            readOnly={!isDraft}
            testid="offer-free-text-after"
          />
          <MarkdownField
            label={t('offers.freeTextBeforeTerms')}
            hint={t('offers.freeTextHint')}
            value={freeTextBefore}
            onChange={(v) => { setFreeTextBefore(v); setIsDirty(true) }}
            onBlur={saveAll}
            readOnly={!isDraft}
            testid="offer-free-text-before"
          />

          {/* Line Items */}
          <div className="rounded-lg border bg-white">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    Pos.
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {t('offers.detail.description')}
                  </th>
                  <th className="px-4 py-2 text-center text-xs font-medium uppercase text-gray-500">
                    {t('offers.detail.qty')}
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                    {t('offers.detail.unitPrice')}
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                    {t('offers.detail.amount')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, idx) => (
                  <tr key={item.item_id || idx} className="border-b">
                    <td className="px-4 py-2 text-sm text-gray-500">
                      {idx + 1}
                    </td>
                    <td className="px-4 py-2 text-sm">
                      <div>{item.product_name}</div>
                      {item.description && (
                        <div className="text-xs text-gray-500">
                          {item.description}
                        </div>
                      )}
                      {item.is_one_off && (
                        <span className="text-xs italic text-gray-400">
                          {t('offers.detail.oneOff')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-center text-sm">
                      {item.quantity}
                    </td>
                    <td className="px-4 py-2 text-right text-sm">
                      {formatCurrency(item.unit_price)}
                    </td>
                    <td className="px-4 py-2 text-right text-sm font-medium">
                      {formatCurrency(item.amount)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t">
                  <td
                    colSpan={4}
                    className="px-4 py-2 text-right text-sm text-gray-500"
                  >
                    {t('offers.detail.netTotal')}
                  </td>
                  <td className="px-4 py-2 text-right text-sm">
                    {formatCurrency(offer.totalNet)}
                  </td>
                </tr>
                {offer.vatSentence ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-2 text-xs italic text-gray-500"
                    >
                      {offer.vatSentence}
                    </td>
                  </tr>
                ) : (
                  <tr>
                    <td
                      colSpan={4}
                      className="px-4 py-2 text-right text-sm text-gray-500"
                    >
                      {t('offers.detail.tax')} ({offer.taxRate}%)
                    </td>
                    <td className="px-4 py-2 text-right text-sm">
                      {formatCurrency(offer.taxAmount)}
                    </td>
                  </tr>
                )}
                <tr className="border-t-2 font-bold">
                  <td
                    colSpan={4}
                    className="px-4 py-2 text-right text-sm"
                  >
                    {t('offers.detail.totalGross')}
                  </td>
                  <td className="px-4 py-2 text-right text-sm">
                    {formatCurrency(offer.totalGross)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Right: PDF Preview */}
        <div>
          {isDraft && (
            <p className="mb-2 text-xs text-gray-500">
              {t('offers.pdfPreviewHint', {
                defaultValue:
                  'PDF wird beim Speichern neu erzeugt. Klick auf „Speichern", um Änderungen zu übernehmen.',
              })}
            </p>
          )}
          {pdfBlobUrl ? (
            <div
              className="overflow-hidden rounded-lg border bg-white"
              style={{ height: '80vh' }}
            >
              <iframe
                src={pdfBlobUrl}
                className="h-full w-full"
                title={`Offer ${offer.offerNumber}`}
              />
            </div>
          ) : (
            <div
              className="flex items-center justify-center rounded-lg border bg-gray-50"
              style={{ height: '40vh' }}
            >
              <div className="text-center text-gray-400">
                <FileText className="mx-auto mb-2 h-12 w-12" />
                <p className="text-sm">{t('offers.detail.noPdf')}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Send Dialog */}
      <SendOfferDialog
        open={showSendDialog}
        onOpenChange={setShowSendDialog}
        offerId={offer.id}
        defaultRecipients={offer.customerBillingEmails || []}
        onSent={() => refetch()}
      />

      {/* Re-create confirmation dialog */}
      <Dialog
        open={showRecreateDialog}
        onOpenChange={setShowRecreateDialog}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('offers.recreateConfirmTitle')}</DialogTitle>
            <DialogDescription>
              {t('offers.recreateConfirmDescription')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setShowRecreateDialog(false)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleRecreate}
              disabled={recreating}
              data-testid="offer-recreate-confirm"
            >
              {recreating && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t('offers.recreateConfirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
