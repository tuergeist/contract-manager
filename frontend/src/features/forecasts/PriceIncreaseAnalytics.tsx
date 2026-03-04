import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'
import { KPICard } from '@/features/dashboard/KPICard'

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
}

export function PriceIncreaseAnalytics() {
  const { t } = useTranslation()
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

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title={t('dashboard.priceIncrease.totalImpact')}
          value={totalImpact}
          explanation={t('dashboard.priceIncrease.totalImpactExplanation')}
          subtitle={t('dashboard.priceIncrease.itemCount', { count: impact?.itemCount ?? 0 })}
          isCurrency
        />
        <KPICard
          title={t('dashboard.priceIncrease.inflation')}
          value={inflationImpact}
          explanation={t('dashboard.priceIncrease.inflationExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.priceIncrease.negotiated')}
          value={negotiatedImpact}
          explanation={t('dashboard.priceIncrease.negotiatedExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.priceIncrease.untagged')}
          value={untaggedImpact}
          explanation={t('dashboard.priceIncrease.untaggedExplanation')}
          isCurrency
        />
      </div>
    </div>
  )
}
