import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import { ArrowLeft, Loader2, ArrowUpDown, Info } from 'lucide-react'
import { formatCurrency } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const NEW_BUSINESS_DETAILS_QUERY = gql`
  query NewBusinessDetails($year: Int!, $metricType: String!) {
    newBusinessDetails(year: $year, metricType: $metricType) {
      customerId
      customerName
      contractId
      contractName
      itemId
      itemDescription
      value
      source
    }
  }
`

interface DetailItem {
  customerId: number
  customerName: string
  contractId: number
  contractName: string
  itemId: number | null
  itemDescription: string | null
  value: string
  source: string
}

const METRIC_LABELS: Record<string, { en: string; de: string }> = {
  new_arr: { en: 'New Name ARR', de: 'New Name ARR' },
  back_to_base_arr: { en: 'Back-to-Base ARR', de: 'Back-to-Base ARR' },
  new_development: { en: 'Won Development', de: 'Won Development' },
  new_deal_count: { en: 'Won Deal Count', de: 'Won Deal Count' },
}

const METRIC_INFO_KEYS: Record<string, string> = {
  new_arr: 'dashboard.kpis.newNameArrExplanation',
  back_to_base_arr: 'dashboard.kpis.backToBaseArrExplanation',
  new_development: 'dashboard.kpis.wonDevelopmentExplanation',
  new_deal_count: 'dashboard.kpis.wonDealCountExplanation',
}

type SortKey = 'customerName' | 'contractName' | 'itemDescription' | 'value'
type SortDir = 'asc' | 'desc'

export function NewBusinessDetailPage() {
  const { t, i18n } = useTranslation()
  const { metricType } = useParams<{ metricType: string }>()
  const [searchParams] = useSearchParams()
  const year = parseInt(searchParams.get('year') || new Date().getFullYear().toString())

  const [sortKey, setSortKey] = useState<SortKey>('value')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const { data, loading } = useQuery(NEW_BUSINESS_DETAILS_QUERY, {
    variables: { year, metricType: metricType || '' },
    skip: !metricType,
  })

  const items: DetailItem[] = data?.newBusinessDetails || []
  const isCurrency = metricType !== 'new_deal_count'

  const sorted = useMemo(() => {
    return [...items].sort((a, b) => {
      let cmp = 0
      if (sortKey === 'value') {
        cmp = parseFloat(a.value) - parseFloat(b.value)
      } else {
        cmp = (a[sortKey] || '').localeCompare(b[sortKey] || '', 'de')
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [items, sortKey, sortDir])

  const total = useMemo(() =>
    items.reduce((sum, r) => sum + parseFloat(r.value), 0),
    [items]
  )

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir(key === 'value' ? 'desc' : 'asc')
    }
  }

  const lang = i18n.language === 'de' ? 'de' : 'en'
  const title = METRIC_LABELS[metricType || '']?.[lang] || metricType

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      className="pb-2 font-medium cursor-pointer select-none hover:text-gray-900"
      onClick={() => toggleSort(field)}
    >
      <div className={`flex items-center gap-1 ${field === 'value' ? 'justify-end' : ''}`}>
        {label}
        <ArrowUpDown className={`h-3 w-3 ${sortKey === field ? 'text-gray-900' : 'text-gray-300'}`} />
      </div>
    </th>
  )

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('common.back')}
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-sm text-muted-foreground">{year} — {items.length} {items.length === 1 ? 'item' : 'items'}{isCurrency && ` — ${t('common.total')}: ${formatCurrency(total.toString())}`}</p>
        </div>
      </div>

      {metricType && METRIC_INFO_KEYS[metricType] && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <Info className="h-4 w-4 mt-0.5 shrink-0" />
          <span>{t(METRIC_INFO_KEYS[metricType])}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <div className="rounded-lg border bg-card">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <SortHeader label={t('contracts.customer')} field="customerName" />
                <SortHeader label={t('nav.contracts')} field="contractName" />
                <SortHeader label={t('dashboard.drilldown.item')} field="itemDescription" />
                {isCurrency && <SortHeader label={t('dashboard.drilldown.value')} field="value" />}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row, i) => (
                <tr key={`${row.contractId}-${row.itemId}-${i}`} className="border-b last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/customers/${row.customerId}`} className="text-blue-600 hover:underline">
                      {row.customerName}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Link to={`/contracts/${row.contractId}`} className="text-blue-600 hover:underline">
                      {row.contractName}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {row.itemDescription || '—'}
                    {row.source === 'expansion' && (
                      <span className="ml-2 inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                        Expansion
                      </span>
                    )}
                  </td>
                  {isCurrency && (
                    <td className="px-4 py-3 text-right font-medium">
                      {formatCurrency(row.value)}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
            {isCurrency && items.length > 0 && (
              <tfoot>
                <tr className="border-t bg-gray-50 font-semibold">
                  <td colSpan={3} className="px-4 py-3">{t('common.total')}</td>
                  <td className="px-4 py-3 text-right">{formatCurrency(total.toString())}</td>
                </tr>
              </tfoot>
            )}
          </table>
          {items.length === 0 && (
            <p className="text-center text-gray-500 py-8">{t('common.noResults')}</p>
          )}
        </div>
      )}
    </div>
  )
}
