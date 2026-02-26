import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  ArrowLeft,
  Loader2,
  Download,
  Send,
  Check,
  X,
  Trash2,
  AlertCircle,
  FileText,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn, formatCurrency, formatDate } from '@/lib/utils'
import { getToken } from '@/lib/auth'
import { SendOfferDialog } from './SendOfferDialog'

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
      createdAt
      lineItemsSnapshot
      notes
      pdfUrl
      vatSentence
      customerBillingEmails
      emailSentAt
      emailSentTo
      emailMessageId
    }
  }
`

const UPDATE_STATUS = gql`
  mutation UpdateOfferStatus($id: Int!, $status: String!) {
    updateOfferStatus(id: $id, status: $status) {
      success
      error
      offer {
        id
        status
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

export function OfferDetail() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showSendDialog, setShowSendDialog] = useState(false)

  const { data, loading, error, refetch } = useQuery(OFFER_QUERY, {
    variables: { id: parseInt(id!) },
    skip: !id,
  })

  const [updateStatus, { loading: updatingStatus }] = useMutation(UPDATE_STATUS)
  const [deleteOffer, { loading: deleting }] = useMutation(DELETE_OFFER)

  const offer = data?.offer

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !offer) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/offers')}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t('common.back')}
        </Button>
        <div className="text-center py-20 text-gray-500">
          <AlertCircle className="w-8 h-8 mx-auto mb-2" />
          {t('offers.detail.notFound')}
        </div>
      </div>
    )
  }

  const today = new Date().toISOString().slice(0, 10)
  const isExpired = offer.validUntil && offer.validUntil < today
  const isDraft = offer.status === 'draft'
  const isSent = offer.status === 'sent'

  // Fetch PDF via authenticated endpoint and create blob URL
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!offer.pdfUrl) return
    const token = getToken()
    fetch(`/api/offers/${offer.id}/pdf/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((blob) => setPdfBlobUrl(URL.createObjectURL(blob)))
      .catch(() => setPdfBlobUrl(null))
    return () => {
      setPdfBlobUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null })
    }
  }, [offer.id, offer.pdfUrl])

  const handleStatusChange = async (newStatus: string) => {
    const result = await updateStatus({
      variables: { id: offer.id, status: newStatus },
    })
    if (result.data?.updateOfferStatus?.success) {
      refetch()
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(t('offers.detail.deleteConfirm'))) return
    const result = await deleteOffer({ variables: { id: offer.id } })
    if (result.data?.deleteOffer?.success) {
      navigate('/offers')
    }
  }

  const lineItems: LineItem[] = offer.lineItemsSnapshot || []

  const statusVariants: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    sent: 'bg-blue-100 text-blue-700',
    accepted: 'bg-green-100 text-green-700',
    rejected: 'bg-red-100 text-red-700',
    cancelled: 'bg-gray-100 text-gray-500',
  }

  const statusLabels: Record<string, string> = {
    draft: t('offers.statusDraft'),
    sent: t('offers.statusSent'),
    accepted: t('offers.statusAccepted'),
    rejected: t('offers.statusRejected'),
    cancelled: t('offers.statusCancelled'),
  }

  return (
    <div className="space-y-6">
      {/* Back + Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/offers')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t('common.back')}
          </Button>
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-3">
              {t('offers.detail.title')} {offer.offerNumber}
              <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', statusVariants[offer.status])}>
                {statusLabels[offer.status] || offer.status}
              </span>
              {isExpired && (isDraft || isSent) && (
                <Badge variant="destructive" className="text-xs">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  {t('offers.statusExpired')}
                </Badge>
              )}
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* Download PDF */}
          {pdfBlobUrl && (
            <Button variant="outline" size="sm" asChild>
              <a href={pdfBlobUrl} target="_blank" rel="noopener noreferrer">
                <Download className="w-4 h-4 mr-2" />
                PDF
              </a>
            </Button>
          )}

          {/* Draft actions */}
          {isDraft && (
            <>
              {offer.pdfUrl && (
                <Button size="sm" onClick={() => setShowSendDialog(true)}>
                  <Send className="w-4 h-4 mr-2" />
                  {t('offers.detail.send')}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={() => handleStatusChange('cancelled')} disabled={updatingStatus}>
                <X className="w-4 h-4 mr-2" />
                {t('offers.detail.cancel')}
              </Button>
              <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleting}>
                <Trash2 className="w-4 h-4 mr-2" />
                {t('common.delete')}
              </Button>
            </>
          )}

          {/* Sent actions */}
          {isSent && (
            <>
              <Button size="sm" variant="default" onClick={() => handleStatusChange('accepted')} disabled={updatingStatus}>
                <Check className="w-4 h-4 mr-2" />
                {t('offers.detail.markAccepted')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleStatusChange('rejected')} disabled={updatingStatus}>
                <X className="w-4 h-4 mr-2" />
                {t('offers.detail.markRejected')}
              </Button>
              <Button size="sm" variant="outline" onClick={() => handleStatusChange('cancelled')} disabled={updatingStatus}>
                {t('offers.detail.cancel')}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Email sent info */}
      {offer.emailSentAt && (
        <div className="text-sm text-gray-500 bg-blue-50 rounded-lg px-4 py-2">
          {t('offers.detail.emailSent', {
            date: formatDate(offer.emailSentAt),
            recipients: (offer.emailSentTo || []).join(', '),
          })}
        </div>
      )}

      {/* Metadata + PDF Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Metadata */}
        <div className="space-y-4">
          <div className="rounded-lg border bg-white p-4 space-y-3">
            <div className="grid grid-cols-2 gap-2 text-sm">
              <span className="text-gray-500">{t('offers.detail.offerDate')}</span>
              <span>{formatDate(offer.offerDate)}</span>

              <span className="text-gray-500">{t('offers.detail.validUntil')}</span>
              <span className={cn(isExpired && 'text-red-600 font-medium')}>
                {offer.validUntil ? formatDate(offer.validUntil) : '—'}
              </span>

              <span className="text-gray-500">{t('offers.detail.customer')}</span>
              <span>
                {offer.customerId ? (
                  <Link to={`/customers/${offer.customerId}`} className="text-primary hover:underline">
                    {offer.customerName}
                  </Link>
                ) : offer.customerName}
              </span>

              <span className="text-gray-500">{t('offers.detail.contract')}</span>
              <span>
                {offer.contractId ? (
                  <Link to={`/contracts/${offer.contractId}`} className="text-primary hover:underline">
                    {offer.contractName}
                  </Link>
                ) : offer.contractName}
              </span>

              <span className="text-gray-500">{t('offers.detail.period')}</span>
              <span>{formatDate(offer.periodStart)} – {formatDate(offer.periodEnd)}</span>

              <span className="text-gray-500">{t('offers.detail.billingDate')}</span>
              <span>{formatDate(offer.billingDate)}</span>
            </div>
          </div>

          {/* Notes */}
          {offer.notes && (
            <div className="rounded-lg border bg-white p-4">
              <h3 className="text-sm font-medium text-gray-500 mb-2">{t('offers.detail.notes')}</h3>
              <p className="text-sm whitespace-pre-wrap">{offer.notes}</p>
            </div>
          )}

          {/* Line Items */}
          <div className="rounded-lg border bg-white">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-gray-50">
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Pos.</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">{t('offers.detail.description')}</th>
                  <th className="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">{t('offers.detail.qty')}</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">{t('offers.detail.unitPrice')}</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">{t('offers.detail.amount')}</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item, idx) => (
                  <tr key={item.item_id || idx} className="border-b">
                    <td className="px-4 py-2 text-sm text-gray-500">{idx + 1}</td>
                    <td className="px-4 py-2 text-sm">
                      <div>{item.product_name}</div>
                      {item.description && (
                        <div className="text-xs text-gray-500">{item.description}</div>
                      )}
                      {item.is_one_off && (
                        <span className="text-xs text-gray-400 italic">{t('offers.detail.oneOff')}</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-sm text-center">{item.quantity}</td>
                    <td className="px-4 py-2 text-sm text-right">{formatCurrency(item.unit_price)}</td>
                    <td className="px-4 py-2 text-sm text-right font-medium">{formatCurrency(item.amount)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t">
                  <td colSpan={4} className="px-4 py-2 text-sm text-right text-gray-500">{t('offers.detail.netTotal')}</td>
                  <td className="px-4 py-2 text-sm text-right">{formatCurrency(offer.totalNet)}</td>
                </tr>
                {offer.vatSentence ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-2 text-xs text-gray-500 italic">{offer.vatSentence}</td>
                  </tr>
                ) : (
                  <tr>
                    <td colSpan={4} className="px-4 py-2 text-sm text-right text-gray-500">
                      {t('offers.detail.tax')} ({offer.taxRate}%)
                    </td>
                    <td className="px-4 py-2 text-sm text-right">{formatCurrency(offer.taxAmount)}</td>
                  </tr>
                )}
                <tr className="border-t-2 font-bold">
                  <td colSpan={4} className="px-4 py-2 text-sm text-right">{t('offers.detail.totalGross')}</td>
                  <td className="px-4 py-2 text-sm text-right">{formatCurrency(offer.totalGross)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* Right: PDF Preview */}
        <div>
          {pdfBlobUrl ? (
            <div className="rounded-lg border bg-white overflow-hidden" style={{ height: '80vh' }}>
              <iframe
                src={pdfBlobUrl}
                className="w-full h-full"
                title={`Offer ${offer.offerNumber}`}
              />
            </div>
          ) : (
            <div className="rounded-lg border bg-gray-50 flex items-center justify-center" style={{ height: '40vh' }}>
              <div className="text-center text-gray-400">
                <FileText className="w-12 h-12 mx-auto mb-2" />
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
    </div>
  )
}
