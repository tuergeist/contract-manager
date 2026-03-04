import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { ArrowLeft, Loader2, FileText, Mail, User, Calendar, Hash } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { formatDateTime } from '@/lib/utils'
import { useDocumentTitle } from '@/lib/useDocumentTitle'

const ORDER_CONFIRMATION_QUERY = gql`
  query OrderConfirmation($id: ID!) {
    orderConfirmation(id: $id) {
      id
      orderConfirmationNumber
      status
      personalMessage
      includeMessageInPdf
      includeMessageInEmail
      additionalEmails
      language
      sentAt
      sentTo
      createdAt
      createdByName
      pdfUrl
      contractId
    }
  }
`

export function OrderConfirmationDetail() {
  const { t } = useTranslation()
  const { id, abId } = useParams<{ id: string; abId: string }>()
  const navigate = useNavigate()

  useDocumentTitle(t('orderConfirmation.detail.title'))

  const { data, loading } = useQuery(ORDER_CONFIRMATION_QUERY, {
    variables: { id: abId },
    skip: !abId,
  })

  const ab = data?.orderConfirmation

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!ab) {
    return (
      <div className="p-8 text-center text-gray-500">
        {t('common.notFound')}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={() => navigate(`/contracts/${id}`)}
            className="mb-2 inline-flex items-center text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('common.back')}
          </button>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="h-6 w-6" />
            {t('orderConfirmation.detail.title')} {ab.orderConfirmationNumber}
          </h1>
        </div>
        {ab.pdfUrl && (
          <a href={ab.pdfUrl} target="_blank" rel="noopener noreferrer">
            <Button variant="outline">
              <FileText className="mr-2 h-4 w-4" />
              PDF
            </Button>
          </a>
        )}
      </div>

      {/* Metadata Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-1">
              <Hash className="h-4 w-4" />
              {t('orderConfirmation.detail.number')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{ab.orderConfirmationNumber}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {t('orderConfirmation.detail.sentDate')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">
              {ab.sentAt ? formatDateTime(ab.sentAt) : '—'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-1">
              <Mail className="h-4 w-4" />
              {t('orderConfirmation.detail.sentTo')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {(ab.sentTo || []).map((email: string, i: number) => (
                <p key={i} className="text-sm">{email}</p>
              ))}
              {(!ab.sentTo || ab.sentTo.length === 0) && <p className="text-sm text-gray-400">—</p>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-500 flex items-center gap-1">
              <User className="h-4 w-4" />
              {t('orderConfirmation.detail.createdBy')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-semibold">{ab.createdByName || '—'}</p>
            <p className="text-xs text-gray-500">{formatDateTime(ab.createdAt)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Personal Message */}
      {ab.personalMessage && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              {t('orderConfirmation.personalMessage')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm">{ab.personalMessage}</p>
          </CardContent>
        </Card>
      )}

      {/* PDF Preview */}
      {ab.pdfUrl && (
        <Card>
          <CardContent className="p-0">
            <iframe
              src={ab.pdfUrl}
              className="h-[700px] w-full rounded-b-lg"
              title="Order Confirmation PDF"
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
