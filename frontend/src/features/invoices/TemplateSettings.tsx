import { useState, useEffect, useRef, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Palette, Upload, Trash2, FileText, Eye, Sparkles, CheckCircle2, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { ExtractionReviewPanel } from './ExtractionReviewPanel'

const TEMPLATE_QUERY = gql`
  query InvoiceTemplate {
    invoiceTemplate {
      accentColor
      headerText
      footerText
      hasLogo
      logoUrl
      references {
        id
        originalFilename
        fileSize
        createdAt
        extractionStatus
        extractedData
      }
    }
    pdfAnalysisAvailable
  }
`

const SAVE_TEMPLATE = gql`
  mutation SaveInvoiceTemplate($input: InvoiceTemplateInput!) {
    saveInvoiceTemplate(input: $input) {
      success
      error
    }
  }
`

const UPLOAD_LOGO = gql`
  mutation UploadInvoiceLogo($input: UploadLogoInput!) {
    uploadInvoiceLogo(input: $input) {
      success
      error
      data { hasLogo logoUrl }
    }
  }
`

const DELETE_LOGO = gql`
  mutation DeleteInvoiceTemplateLogo {
    deleteInvoiceTemplateLogo {
      success
      error
    }
  }
`

const UPLOAD_REFERENCE = gql`
  mutation UploadInvoiceReferencePdf($input: UploadReferencePdfInput!) {
    uploadInvoiceReferencePdf(input: $input) {
      success
      error
    }
  }
`

const DELETE_REFERENCE = gql`
  mutation DeleteInvoiceTemplateReference($referenceId: Int!) {
    deleteInvoiceTemplateReference(referenceId: $referenceId) {
      success
      error
    }
  }
`

const ANALYZE_REFERENCE = gql`
  mutation AnalyzeReferencePdf($referenceId: Int!) {
    analyzeReferencePdf(referenceId: $referenceId) {
      success
      error
      extractedData
    }
  }
`

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

interface ReferenceData {
  id: number
  originalFilename: string
  fileSize: number
  createdAt: string
  extractionStatus: string
  extractedData: Record<string, unknown> | null
}

interface TemplateSettingsProps {
  showHeader?: boolean
}

export function TemplateSettings({ showHeader = true }: TemplateSettingsProps) {
  const { t, i18n } = useTranslation()
  const [accentColor, setAccentColor] = useState('#2563eb')
  const [headerText, setHeaderText] = useState('')
  const [footerText, setFooterText] = useState('')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [analyzingRefId, setAnalyzingRefId] = useState<number | null>(null)
  const [expandedRefId, setExpandedRefId] = useState<number | null>(null)
  const logoInputRef = useRef<HTMLInputElement>(null)
  const refInputRef = useRef<HTMLInputElement>(null)

  const { data, loading, refetch } = useQuery(TEMPLATE_QUERY)
  const [saveTemplate, { loading: saving }] = useMutation(SAVE_TEMPLATE)
  const [uploadLogo, { loading: uploadingLogo }] = useMutation(UPLOAD_LOGO)
  const [deleteLogo] = useMutation(DELETE_LOGO)
  const [uploadReference, { loading: uploadingRef }] = useMutation(UPLOAD_REFERENCE)
  const [deleteReference] = useMutation(DELETE_REFERENCE)
  const [analyzeReference] = useMutation(ANALYZE_REFERENCE)

  const pdfAnalysisAvailable = data?.pdfAnalysisAvailable ?? false

  useEffect(() => {
    if (data?.invoiceTemplate) {
      const t = data.invoiceTemplate
      setAccentColor(t.accentColor || '#2563eb')
      setHeaderText(t.headerText || '')
      setFooterText(t.footerText || '')
    }
  }, [data])

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const { data: result } = await saveTemplate({
        variables: { input: { accentColor, headerText, footerText } },
        refetchQueries: ['InvoiceTemplate'],
      })
      if (result?.saveInvoiceTemplate?.success) {
        showToast('success', t('invoices.template.saved'))
      } else {
        showToast('error', result?.saveInvoiceTemplate?.error || t('invoices.template.saveFailed'))
      }
    } catch {
      showToast('error', t('invoices.template.saveFailed'))
    }
  }

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async () => {
      const base64 = (reader.result as string).split(',')[1]
      try {
        const { data: result } = await uploadLogo({
          variables: { input: { fileContent: base64, filename: file.name } },
        })
        if (result?.uploadInvoiceLogo?.success) {
          refetch()
        } else {
          showToast('error', result?.uploadInvoiceLogo?.error || t('invoices.template.saveFailed'))
        }
      } catch {
        showToast('error', t('invoices.template.saveFailed'))
      }
    }
    reader.readAsDataURL(file)
    // Reset input so same file can be re-selected
    e.target.value = ''
  }

  const handleDeleteLogo = async () => {
    await deleteLogo({ refetchQueries: ['InvoiceTemplate'] })
    refetch()
  }

  const handleReferenceUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = async () => {
      const base64 = (reader.result as string).split(',')[1]
      try {
        const { data: result } = await uploadReference({
          variables: { input: { fileContent: base64, filename: file.name } },
        })
        if (result?.uploadInvoiceReferencePdf?.success) {
          refetch()
        } else {
          showToast('error', result?.uploadInvoiceReferencePdf?.error || t('invoices.template.saveFailed'))
        }
      } catch {
        showToast('error', t('invoices.template.saveFailed'))
      }
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleDeleteReference = async (id: number) => {
    if (expandedRefId === id) setExpandedRefId(null)
    await deleteReference({
      variables: { referenceId: id },
      refetchQueries: ['InvoiceTemplate'],
    })
    refetch()
  }

  const handleAnalyzeReference = async (id: number) => {
    setAnalyzingRefId(id)
    try {
      const { data: result } = await analyzeReference({
        variables: { referenceId: id },
        refetchQueries: ['InvoiceTemplate'],
      })
      if (result?.analyzeReferencePdf?.success) {
        showToast('success', t('invoices.extraction.success'))
        setExpandedRefId(id)
      } else {
        showToast('error', result?.analyzeReferencePdf?.error || t('invoices.extraction.failed'))
      }
    } catch {
      showToast('error', t('invoices.extraction.failed'))
    } finally {
      setAnalyzingRefId(null)
    }
  }

  const handleApplyTemplate = (design: { accent_color: string | null; header_text: string | null; footer_text: string | null }) => {
    if (design.accent_color) setAccentColor(design.accent_color)
    if (design.header_text !== null && design.header_text !== undefined) setHeaderText(design.header_text)
    if (design.footer_text !== null && design.footer_text !== undefined) setFooterText(design.footer_text)
    showToast('success', t('invoices.extraction.appliedTemplate'))
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handlePreview = useCallback(async () => {
    // Revoke previous URL to avoid memory leaks
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setLoadingPreview(true)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(
        `/api/invoices/preview/?language=${i18n.language}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!response.ok) throw new Error('Preview failed')
      const blob = await response.blob()
      setPreviewUrl(URL.createObjectURL(blob))
    } catch {
      showToast('error', t('invoices.template.previewFailed'))
    } finally {
      setLoadingPreview(false)
    }
  }, [i18n.language, previewUrl, t])

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const inputClass = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
  const labelClass = "block text-sm font-medium text-gray-700 mb-1"
  const template = data?.invoiceTemplate

  return (
    <div className="mx-auto max-w-2xl">
      {showHeader && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Palette className="h-6 w-6 text-gray-600" />
            <h1 className="text-2xl font-bold text-gray-900">{t('invoices.template.title')}</h1>
          </div>
          <p className="text-sm text-gray-500">{t('invoices.template.description')}</p>
        </div>
      )}

      {toast && (
        <div className={`mb-4 rounded-lg px-4 py-3 text-sm ${toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {toast.message}
        </div>
      )}

      <div className="space-y-6">
        {/* Logo */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.template.logo')}</h2>
          {template?.hasLogo && template?.logoUrl ? (
            <div className="mb-4 flex items-center gap-4">
              <img src={template.logoUrl} alt="Logo" className="h-16 max-w-[200px] object-contain rounded border p-2" />
              <button onClick={handleDeleteLogo} className="flex items-center gap-1 text-sm text-red-600 hover:text-red-700">
                <Trash2 className="h-4 w-4" /> {t('invoices.template.deleteLogo')}
              </button>
            </div>
          ) : null}
          <input ref={logoInputRef} type="file" accept=".png,.jpg,.jpeg,.svg" className="hidden" onChange={handleLogoUpload} />
          <button
            type="button"
            onClick={() => logoInputRef.current?.click()}
            disabled={uploadingLogo}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {uploadingLogo ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {t('invoices.template.uploadLogo')}
          </button>
          <p className="mt-2 text-xs text-gray-500">{t('invoices.template.logoHint')}</p>
        </section>

        {/* Template Settings Form */}
        <form onSubmit={handleSave}>
          <section className="rounded-lg border bg-white p-6 space-y-4">
            <div>
              <label className={labelClass}>{t('invoices.template.accentColor')}</label>
              <div className="flex items-center gap-3">
                <input
                  type="color"
                  value={accentColor}
                  onChange={e => setAccentColor(e.target.value)}
                  className="h-10 w-10 cursor-pointer rounded border-0 p-0"
                />
                <input
                  className={`${inputClass} max-w-[120px] font-mono`}
                  value={accentColor}
                  onChange={e => setAccentColor(e.target.value)}
                  maxLength={7}
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>{t('invoices.template.headerText')}</label>
              <input className={inputClass} value={headerText} onChange={e => setHeaderText(e.target.value)} placeholder={t('invoices.template.headerTextPlaceholder')} />
            </div>

            <div>
              <label className={labelClass}>{t('invoices.template.footerText')}</label>
              <textarea className={`${inputClass} min-h-[80px]`} value={footerText} onChange={e => setFooterText(e.target.value)} placeholder={t('invoices.template.footerTextPlaceholder')} rows={3} />
            </div>

            <div className="flex justify-end pt-2">
              <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                {t('common.save')}
              </button>
            </div>
          </section>
        </form>

        {/* Reference PDFs */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.template.references')}</h2>
          <p className="mb-4 text-xs text-gray-500">{t('invoices.template.referenceHint')}</p>

          {template?.references?.length > 0 ? (
            <div className="mb-4 space-y-3">
              {template.references.map((ref: ReferenceData) => {
                const isAnalyzing = analyzingRefId === ref.id
                const isExpanded = expandedRefId === ref.id
                const hasResults = ref.extractionStatus === 'completed' && ref.extractedData

                return (
                  <div key={ref.id} className="rounded-lg border">
                    <div className="flex items-center justify-between px-4 py-3">
                      <div className="flex items-center gap-3">
                        <FileText className="h-5 w-5 text-gray-400" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{ref.originalFilename}</p>
                          <p className="text-xs text-gray-500">{formatFileSize(ref.fileSize)}</p>
                        </div>
                        {/* Extraction status indicator */}
                        {ref.extractionStatus === 'completed' && (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        {ref.extractionStatus === 'failed' && (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        {isAnalyzing && (
                          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {/* View Results toggle */}
                        {hasResults && (
                          <button
                            onClick={() => setExpandedRefId(isExpanded ? null : ref.id)}
                            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50"
                          >
                            {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                            {t('invoices.extraction.viewResults')}
                          </button>
                        )}
                        {/* Extract / Retry button */}
                        {pdfAnalysisAvailable && (
                          <button
                            onClick={() => handleAnalyzeReference(ref.id)}
                            disabled={isAnalyzing}
                            className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-purple-600 hover:bg-purple-50 disabled:opacity-50"
                            title={ref.extractionStatus === 'failed' ? t('invoices.extraction.retry') : t('invoices.extraction.extract')}
                          >
                            {isAnalyzing ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Sparkles className="h-3 w-3" />
                            )}
                            {ref.extractionStatus === 'failed'
                              ? t('invoices.extraction.retry')
                              : ref.extractionStatus === 'completed'
                                ? t('invoices.extraction.reExtract')
                                : t('invoices.extraction.extract')}
                          </button>
                        )}
                        <button onClick={() => handleDeleteReference(ref.id)} className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    {/* Expanded review panel */}
                    {isExpanded && hasResults && (
                      <div className="border-t px-4 py-4">
                        <ExtractionReviewPanel
                          data={ref.extractedData as never}
                          onClose={() => setExpandedRefId(null)}
                          onApplyTemplate={handleApplyTemplate}
                        />
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <p className="mb-4 text-sm text-gray-400">{t('invoices.template.noReferences')}</p>
          )}

          <input ref={refInputRef} type="file" accept=".pdf" className="hidden" onChange={handleReferenceUpload} />
          <button
            type="button"
            onClick={() => refInputRef.current?.click()}
            disabled={uploadingRef}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {uploadingRef ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            {t('invoices.template.uploadReference')}
          </button>
        </section>

        {/* Preview */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.template.preview')}</h2>
          <p className="mb-4 text-xs text-gray-500">{t('invoices.template.previewHint')}</p>
          <button
            type="button"
            onClick={handlePreview}
            disabled={loadingPreview}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {loadingPreview ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
            {t('invoices.template.showPreview')}
          </button>
          {previewUrl && (
            <div className="mt-4 rounded-lg border overflow-hidden">
              <iframe
                src={previewUrl}
                title="Invoice Preview"
                className="h-[800px] w-full"
              />
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
