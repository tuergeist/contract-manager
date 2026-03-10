import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const COST_CENTER_REPORT = gql`
  query CostCenterReport($dateFrom: Date!, $dateTo: Date!) {
    costCenterReport(dateFrom: $dateFrom, dateTo: $dateTo) {
      dateFrom dateTo
      rows {
        costCenter { id code name }
        label totalAmount transactionCount
      }
    }
  }
`

function getDefaultDates() {
  const now = new Date()
  const from = new Date(now.getFullYear(), now.getMonth(), 1)
  const to = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return {
    from: from.toISOString().split('T')[0],
    to: to.toISOString().split('T')[0],
  }
}

export function CostCenterReportPage() {
  const { t } = useTranslation()
  const defaults = getDefaultDates()
  const [dateFrom, setDateFrom] = useState(defaults.from)
  const [dateTo, setDateTo] = useState(defaults.to)

  const { data, loading } = useQuery(COST_CENTER_REPORT, {
    variables: { dateFrom, dateTo },
    skip: !dateFrom || !dateTo,
  })

  const rows = data?.costCenterReport?.rows || []
  const grandTotal = rows.reduce((s: number, r: any) => s + parseFloat(r.totalAmount), 0)

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('costCenterReport.title')}</h2>

      <div className="flex items-center gap-4">
        <div>
          <label className="text-sm font-medium">{t('costCenterReport.dateFrom')}</label>
          <input
            type="date"
            className="ml-2 rounded-md border px-3 py-2 text-sm"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium">{t('costCenterReport.dateTo')}</label>
          <input
            type="date"
            className="ml-2 rounded-md border px-3 py-2 text-sm"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
          />
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 font-medium">{t('costCenterReport.costCenter')}</th>
              <th className="py-2 font-medium text-right">{t('costCenterReport.totalAmount')}</th>
              <th className="py-2 font-medium text-right">{t('costCenterReport.transactionCount')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any, i: number) => (
              <tr key={i} className="border-b">
                <td className="py-2">{row.label}</td>
                <td className="py-2 text-right">{parseFloat(row.totalAmount).toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}</td>
                <td className="py-2 text-right">{row.transactionCount}</td>
              </tr>
            ))}
            {rows.length > 0 && (
              <tr className="font-semibold">
                <td className="py-2">{t('costCenterReport.total')}</td>
                <td className="py-2 text-right">{grandTotal.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}</td>
                <td></td>
              </tr>
            )}
            {rows.length === 0 && (
              <tr><td colSpan={3} className="py-4 text-center text-muted-foreground">{t('costCenterReport.noData')}</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}
