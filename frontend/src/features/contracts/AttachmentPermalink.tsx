import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Loader2, AlertTriangle, Download } from 'lucide-react'
import { getToken } from '@/lib/auth'
import { useDocumentTitle } from '@/lib/useDocumentTitle'

export function AttachmentPermalink() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [contentType, setContentType] = useState<string>('')
  const [filename, setFilename] = useState<string>('')

  useDocumentTitle(filename || t('attachments.title'))

  useEffect(() => {
    if (!id) return

    const token = getToken()
    fetch(`/api/attachments/${id}/permalink/`, {
      headers: {
        Authorization: token ? `Bearer ${token}` : '',
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(response.statusText)
        }
        const ct = response.headers.get('Content-Type') || ''
        setContentType(ct)
        const disposition = response.headers.get('Content-Disposition') || ''
        const match = disposition.match(/filename="(.+)"/)
        if (match) setFilename(match[1])
        return response.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(new Blob([blob], { type: contentType || undefined }))
        setBlobUrl(url)
        setLoading(false)
      })
      .catch(() => {
        setError(t('attachments.notFound'))
        setLoading(false)
      })

    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl)
    }
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleDownload = () => {
    if (!blobUrl || !filename) return
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-4 text-gray-600">{error}</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const isEmbeddable = contentType.startsWith('image/') ||
    contentType === 'application/pdf' ||
    contentType.startsWith('text/')

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      <div className="flex items-center justify-between border-b bg-white px-6 py-3">
        <span className="text-sm font-medium text-gray-900">{filename}</span>
        <button
          onClick={handleDownload}
          className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
        >
          <Download className="h-4 w-4" />
          {t('attachments.download')}
        </button>
      </div>
      {isEmbeddable && blobUrl ? (
        <iframe
          src={blobUrl}
          className="flex-1 w-full border-0"
          title={filename}
        />
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <div className="text-center">
            <p className="text-gray-600">{filename}</p>
            <button
              onClick={handleDownload}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Download className="h-4 w-4" />
              {t('attachments.download')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
