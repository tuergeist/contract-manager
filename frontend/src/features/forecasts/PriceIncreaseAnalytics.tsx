import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'
import { KPICard } from '@/features/dashboard/KPICard'
import { formatCurrency } from '@/lib/utils'

const PRICE_INCREASE_IMPACT_QUERY = gql`
  query PriceIncreaseImpact($year: Int!) {
    priceIncreaseImpact(year: $year) {
      year
      totalArrImpact
      inflationArrImpact
      negotiatedArrImpact
      untaggedArrImpact
      itemCount
    }
    contractPriceIncreases(year: $year) {
      contractId
      contractName
      customerName
      currentArr
      previousArr
      arrDiff
      itemCount
    }
  }
`

interface PriceIncreaseImpactData {
  priceIncreaseImpact: {
    year: number
    totalArrImpact: string
    inflationArrImpact: string
    negotiatedArrImpact: string
    untaggedArrImpact: string
    itemCount: number
  }
  contractPriceIncreases: {
    contractId: string
    contractName: string
    customerName: string
    currentArr: string
    previousArr: string
    arrDiff: string
    itemCount: number
  }[]
}

export function PriceIncreaseAnalytics() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)

  const { data, loading } = useQuery<PriceIncreaseImpactData>(PRICE_INCREASE_IMPACT_QUERY, {
    variables: { year },
  })

  const years = Array.from({ length: 5 }, (_, i) => currentYear - 2 + i)

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const impact = data?.priceIncreaseImpact
  const totalImpact = parseFloat(impact?.totalArrImpact ?? '0')
  const inflationImpact = parseFloat(impact?.inflationArrImpact ?? '0')
  const negotiatedImpact = parseFloat(impact?.negotiatedArrImpact ?? '0')
  const untaggedImpact = parseFloat(impact?.untaggedArrImpact ?? '0')
  const contracts = data?.contractPriceIncreases ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold">{t('dashboard.priceIncrease.title')}</h2>
        <select
          value={year}
          onChange={(e) => setYear(parseInt(e.target.value))}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          {years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      <div
        className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 cursor-pointer"
        onClick={() => navigate(`/contracts?priceIncrease=true&year=${year}`)}
      >
        <KPICard
          title={t('dashboard.priceIncrease.totalImpact')}
          value={totalImpact}
          explanation={t('dashboard.priceIncrease.totalImpactExplanation')}
          subtitle={t('dashboard.priceIncrease.itemCount', { count: impact?.itemCount ?? 0 })}
          isCurrency
          className="hover:border-blue-300 hover:shadow-sm transition-all"
        />
        <KPICard
          title={t('dashboard.priceIncrease.inflation')}
          value={inflationImpact}
          explanation={t('dashboard.priceIncrease.inflationExplanation')}
          isCurrency
          className="hover:border-blue-300 hover:shadow-sm transition-all"
        />
        <KPICard
          title={t('dashboard.priceIncrease.negotiated')}
          value={negotiatedImpact}
          explanation={t('dashboard.priceIncrease.negotiatedExplanation')}
          isCurrency
          className="hover:border-blue-300 hover:shadow-sm transition-all"
        />
        <KPICard
          title={t('dashboard.priceIncrease.untagged')}
          value={untaggedImpact}
          explanation={t('dashboard.priceIncrease.untaggedExplanation')}
          isCurrency
          className="hover:border-blue-300 hover:shadow-sm transition-all"
        />
      </div>

      {contracts.length > 0 && (
        <div className="overflow-hidden rounded-lg border">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('contracts.form.name')}
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('contracts.customer')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('contracts.previousArr')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('contracts.arr')}
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('contracts.arrDiff')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {contracts.map((c) => (
                <tr key={c.contractId} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4">
                    <Link
                      to={`/contracts/${c.contractId}`}
                      className="font-medium text-blue-600 hover:text-blue-800"
                    >
                      {c.contractName || '—'}
                    </Link>
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-900">
                    {c.customerName}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500 text-right">
                    {formatCurrency(c.previousArr)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900 text-right">
                    {formatCurrency(c.currentArr)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-emerald-600 text-right">
                    +{formatCurrency(c.arrDiff)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
