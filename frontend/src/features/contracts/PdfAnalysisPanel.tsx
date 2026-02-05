import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, X, Check, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const ANALYZE_PDF_QUERY = gql`
  query AnalyzePdfAttachment($attachmentId: ID!) {
    analyzePdfAttachment(attachmentId: $attachmentId) {
      error
      items {
        extracted {
          description
          quantity
          unitPrice
          pricePeriod
          isOneOff
        }
        productMatch {
          productId
          productName
          confidence
        }
        status
        existingItemId
        priceDiffers
      }
      metadata {
        poNumber
        orderConfirmationNumber
        minDurationMonths
      }
      metadataComparisons {
        fieldName
        extractedValue
        currentValue
        differs
      }
    }
  }
`

const IMPORT_PDF_MUTATION = gql`
  mutation ImportPdfAnalysis($input: ImportPdfAnalysisInput!) {
    importPdfAnalysis(input: $input) {
      success
      error
      createdItemsCount
      updatedItemsCount
    }
  }
`

const PRODUCTS_QUERY = gql`
  query ProductsForPdfAnalysis {
    products(page: 1, pageSize: 200, sortBy: "name", sortOrder: "asc") {
      items {
        id
        name
        isActive
      }
    }
  }
`

interface PdfAnalysisPanelProps {
  contractId: string
  attachmentId: string
  onClose: () => void
  onImported: () => void
}

interface ComparisonItem {
  extracted: {
    description: string
    quantity: number
    unitPrice: string
    pricePeriod: string
    isOneOff: boolean
  }
  productMatch: {
    productId: number
    productName: string
    confidence: number
  } | null
  status: string
  existingItemId: number | null
  priceDiffers: boolean
}

interface MetadataComparison {
  fieldName: string
  extractedValue: string | null
  currentValue: string | null
  differs: boolean
}

const METADATA_LABEL_KEYS: Record<string, string> = {
  po_number: 'pdfAnalysis.poNumber',
  order_confirmation_number: 'pdfAnalysis.orderConfirmationNumber',
  min_duration_months: 'pdfAnalysis.minDurationMonths',
}

const PERIOD_LABELS: Record<string, string> = {
  monthly: 'Monthly',
  quarterly: 'Quarterly',
  semi_annual: 'Semi-annual',
  annual: 'Annual',
}

export function PdfAnalysisPanel({
  contractId,
  attachmentId,
  onClose,
  onImported,
}: PdfAnalysisPanelProps) {
  const { t } = useTranslation()

  const { data, loading, error } = useQuery(ANALYZE_PDF_QUERY, {
    variables: { attachmentId },
  })

  const { data: productsData } = useQuery(PRODUCTS_QUERY)

  const [importPdf, { loading: importing }] = useMutation(IMPORT_PDF_MUTATION)

  const [selectedItems, setSelectedItems] = useState<Record<number, boolean>>({})
  const [selectedMetadata, setSelectedMetadata] = useState<Record<string, boolean>>({})
  const [productOverrides, setProductOverrides] = useState<Record<number, string>>({})
  const [importError, setImportError] = useState<string | null>(null)
  const [initialized, setInitialized] = useState(false)

  const analysisResult = data?.analyzePdfAttachment
  const products = (productsData?.products?.items || []).filter(
    (p: { isActive: boolean }) => p.isActive
  )

  // Initialize selection state once data loads
  if (analysisResult && !analysisResult.error && !initialized) {
    const items: Record<number, boolean> = {}
    analysisResult.items.forEach((_: ComparisonItem, idx: number) => {
      items[idx] = false
    })
    setSelectedItems(items)

    const meta: Record<string, boolean> = {}
    analysisResult.metadataComparisons.forEach((mc: MetadataComparison) => {
      meta[mc.fieldName] = mc.differs
    })
    setSelectedMetadata(meta)
    setInitialized(true)
  }

  const handleImport = async () => {
    if (!analysisResult) return
    setImportError(null)

    const itemsToImport = analysisResult.items
      .map((item: ComparisonItem, idx: number) => ({ item, idx }))
      .filter(({ idx }: { idx: number }) => selectedItems[idx])
      .map(({ item, idx }: { item: ComparisonItem; idx: number }) => {
        const overrideProductId = productOverrides[idx]
        const productId =
          overrideProductId || (item.productMatch ? String(item.productMatch.productId) : null)
        return {
          description: item.extracted.description,
          quantity: item.extracted.quantity,
          unitPrice: item.extracted.unitPrice,
          pricePeriod: item.extracted.pricePeriod,
          isOneOff: item.extracted.isOneOff,
          productId,
          ...(item.existingItemId ? { existingItemId: String(item.existingItemId) } : {}),
        }
      })

    const metadata: Record<string, string | number | null> = {}
    let hasMetadata = false
    analysisResult.metadataComparisons.forEach((mc: MetadataComparison) => {
      if (selectedMetadata[mc.fieldName] && mc.extractedValue != null) {
        if (mc.fieldName === 'min_duration_months') {
          metadata.minDurationMonths = parseInt(mc.extractedValue, 10)
        } else if (mc.fieldName === 'po_number') {
          metadata.poNumber = mc.extractedValue
        } else if (mc.fieldName === 'order_confirmation_number') {
          metadata.orderConfirmationNumber = mc.extractedValue
        }
        hasMetadata = true
      }
    })

    try {
      const result = await importPdf({
        variables: {
          input: {
            contractId,
            items: itemsToImport,
            ...(hasMetadata ? { metadata } : {}),
          },
        },
      })

      if (result.data?.importPdfAnalysis?.success) {
        onImported()
      } else {
        setImportError(result.data?.importPdfAnalysis?.error || t('pdfAnalysis.importError'))
      }
    } catch {
      setImportError(t('pdfAnalysis.importError'))
    }
  }

  const selectedNewItems = analysisResult
    ? analysisResult.items.filter(
        (item: ComparisonItem, idx: number) => selectedItems[idx] && item.status !== 'existing'
      )
    : []
  const selectedExistingItems = analysisResult
    ? analysisResult.items.filter(
        (item: ComparisonItem, idx: number) => selectedItems[idx] && item.status === 'existing'
      )
    : []
  const selectedMetadataFields = analysisResult
    ? analysisResult.metadataComparisons.filter(
        (mc: MetadataComparison) => selectedMetadata[mc.fieldName]
      )
    : []
  const metadataOverwrites = selectedMetadataFields.filter(
    (mc: MetadataComparison) => mc.currentValue && mc.differs
  )
  const selectedCount = selectedNewItems.length + selectedExistingItems.length + selectedMetadataFields.length

  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border bg-white p-8">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
          <span className="text-gray-600">{t('pdfAnalysis.analyzing')}</span>
        </div>
      </div>
    )
  }

  // Error state
  if (error || analysisResult?.error) {
    return (
      <div className="rounded-lg border bg-white p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="h-5 w-5" />
            <span>{analysisResult?.error || t('pdfAnalysis.error')}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>
    )
  }

  if (!analysisResult) return null

  return (
    <div className="rounded-lg border bg-white" data-testid="pdf-analysis-panel">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h3 className="text-lg font-semibold">{t('pdfAnalysis.panelTitle')}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="p-6 space-y-6">
        {/* Metadata Comparison */}
        {analysisResult.metadataComparisons.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">
              {t('pdfAnalysis.metadataSection')}
            </h4>
            <div className="overflow-hidden rounded-lg border">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="w-10 px-4 py-2" />
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                      Field
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                      {t('pdfAnalysis.extractedValue')}
                    </th>
                    <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                      {t('pdfAnalysis.currentValue')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {analysisResult.metadataComparisons.map((mc: MetadataComparison) => (
                    <tr key={mc.fieldName}>
                      <td className="px-4 py-2">
                        <Checkbox
                          checked={selectedMetadata[mc.fieldName] || false}
                          onCheckedChange={(checked) =>
                            setSelectedMetadata((prev) => ({
                              ...prev,
                              [mc.fieldName]: !!checked,
                            }))
                          }
                        />
                      </td>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">
                        {t(METADATA_LABEL_KEYS[mc.fieldName] || mc.fieldName)}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-700">
                        {mc.extractedValue || '-'}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-500">
                        {mc.currentValue || '-'}
                        {mc.differs && (
                          <span className="ml-2 text-xs text-amber-600">
                            ({t('pdfAnalysis.priceDiffers')})
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Line Items Table */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-3">
            {t('pdfAnalysis.itemsSection')}
          </h4>
          <div className="overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="w-10 px-4 py-2" />
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.description')}
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.quantity')}
                  </th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.unitPrice')}
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.period')}
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.matchedProduct')}
                  </th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                    {t('pdfAnalysis.status')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {analysisResult.items.map((item: ComparisonItem, idx: number) => {
                  const isExisting = item.status === 'existing'
                  const currentProductId =
                    productOverrides[idx] ||
                    (item.productMatch ? String(item.productMatch.productId) : '')

                  return (
                    <tr
                      key={idx}
                      className={isExisting ? 'bg-gray-50' : ''}
                    >
                      <td className="px-4 py-2">
                        <Checkbox
                          checked={selectedItems[idx] || false}
                          onCheckedChange={(checked) =>
                            setSelectedItems((prev) => ({ ...prev, [idx]: !!checked }))
                          }
                        />
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-900">
                        {item.extracted.description}
                        {item.extracted.isOneOff && (
                          <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
                            One-off
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-right text-sm text-gray-700">
                        {item.extracted.quantity}
                      </td>
                      <td className="px-4 py-2 text-right text-sm text-gray-700">
                        {parseFloat(item.extracted.unitPrice).toLocaleString('de-DE', {
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2,
                        })}
                      </td>
                      <td className="px-4 py-2 text-sm text-gray-700">
                        {PERIOD_LABELS[item.extracted.pricePeriod] || item.extracted.pricePeriod}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        <Select
                          value={currentProductId}
                          onValueChange={(value) =>
                            setProductOverrides((prev) => ({ ...prev, [idx]: value }))
                          }
                        >
                          <SelectTrigger className="h-8 w-48 text-xs">
                            <SelectValue placeholder={t('pdfAnalysis.selectProduct')} />
                          </SelectTrigger>
                          <SelectContent>
                            {products.map((p: { id: string; name: string }) => (
                              <SelectItem key={p.id} value={p.id}>
                                {p.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        {item.productMatch && (
                          <span className="mt-1 block text-xs text-gray-400">
                            {t('pdfAnalysis.confidence')}:{' '}
                            {Math.round(item.productMatch.confidence * 100)}%
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-sm">
                        {isExisting ? (
                          <span className="inline-flex items-center gap-1 text-gray-500">
                            <Check className="h-3 w-3" />
                            {t('pdfAnalysis.statusExisting')}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-green-600">
                            {t('pdfAnalysis.statusNew')}
                          </span>
                        )}
                        {item.priceDiffers && (
                          <span className="ml-1 text-xs text-amber-600">
                            ({t('pdfAnalysis.priceDiffers')})
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Import Summary */}
        {selectedCount > 0 && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm space-y-2">
            <h4 className="font-semibold text-blue-900">{t('pdfAnalysis.importSummaryTitle')}</h4>
            {selectedNewItems.length > 0 && (
              <p className="text-blue-800">
                {t('pdfAnalysis.summaryAddItems', { count: selectedNewItems.length })}
              </p>
            )}
            {selectedExistingItems.length > 0 && (
              <p className="text-amber-800">
                {t('pdfAnalysis.summaryUpdateItems', { count: selectedExistingItems.length })}
              </p>
            )}
            {selectedMetadataFields.length > 0 && metadataOverwrites.length === 0 && (
              <p className="text-blue-800">
                {t('pdfAnalysis.summarySetMetadata', { count: selectedMetadataFields.length })}
              </p>
            )}
            {metadataOverwrites.length > 0 && (
              <div className="text-amber-800 bg-amber-50 border border-amber-200 rounded p-3 -mx-1">
                <p className="font-medium">
                  {t('pdfAnalysis.summaryOverwriteMetadata', { count: metadataOverwrites.length })}
                </p>
                <ul className="mt-1 space-y-0.5 ml-4 list-disc">
                  {metadataOverwrites.map((mc: MetadataComparison) => (
                    <li key={mc.fieldName}>
                      {t(METADATA_LABEL_KEYS[mc.fieldName] || mc.fieldName)}:{' '}
                      <span className="line-through text-amber-600">{mc.currentValue}</span>
                      {' → '}
                      <span className="font-medium">{mc.extractedValue}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-blue-700 text-xs">{t('pdfAnalysis.summaryNoDeleteNote')}</p>
          </div>
        )}

        {/* Import Error */}
        {importError && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {importError}
          </div>
        )}

        {/* Action Bar */}
        <div className="flex items-center justify-end gap-3 border-t pt-4">
          <Button variant="outline" onClick={onClose} disabled={importing}>
            {t('pdfAnalysis.cancel')}
          </Button>
          <Button
            onClick={handleImport}
            disabled={importing || selectedCount === 0}
          >
            {importing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('pdfAnalysis.importSelected')} ({selectedCount})
          </Button>
        </div>
      </div>
    </div>
  )
}
