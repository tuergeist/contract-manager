import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import { Loader2, AlertCircle } from 'lucide-react'
import { KPICard } from './KPICard'
import { HelpVideoButton } from '@/components/HelpVideoButton'
import { formatCurrency } from '@/lib/utils'

const DASHBOARD_KPIS_QUERY = gql`
  query DashboardKPIs($year: Int!) {
    dashboardKpis {
      totalActiveContracts
      totalContractValue
      annualRecurringRevenue
      yearToDateRevenue
      currentYearForecast
      currentYearOneOff
      currentYearDiscounts
      nextYearForecast
      nextYearOneOff
      nextYearDiscounts
    }
    newBusinessMetrics(year: $year) {
      wonNewArr
      wonDevelopmentRevenue
      wonDealCount
    }
    newBusinessGoals(year: $year) {
      id
      year
      goalType
      targetAmount
    }
  }
`


interface DashboardKPIs {
  totalActiveContracts: number
  totalContractValue: string
  annualRecurringRevenue: string
  yearToDateRevenue: string
  currentYearForecast: string
  currentYearOneOff: string
  currentYearDiscounts: string
  nextYearForecast: string
  nextYearOneOff: string
  nextYearDiscounts: string
}

interface NewBusinessMetrics {
  wonNewArr: string
  wonDevelopmentRevenue: string
  wonDealCount: number
}

interface NewBusinessGoal {
  id: number
  year: number
  goalType: string
  targetAmount: string
}

interface DashboardKPIsData {
  dashboardKpis: DashboardKPIs
  newBusinessMetrics: NewBusinessMetrics
  newBusinessGoals: NewBusinessGoal[]
}

export function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const currentYear = new Date().getFullYear()
  const { data: kpisData, loading: kpisLoading, error: kpisError } = useQuery<DashboardKPIsData>(DASHBOARD_KPIS_QUERY, {
    variables: { year: currentYear },
  })
  if (kpisLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (kpisError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-destructive">
        <AlertCircle className="h-8 w-8 mb-2" />
        <p>{t('common.error')}: {kpisError.message}</p>
      </div>
    )
  }

  const kpis = kpisData?.dashboardKpis
  const nb = kpisData?.newBusinessMetrics
  const nbGoalMap: Record<string, number> = {}
  for (const g of kpisData?.newBusinessGoals || []) {
    nbGoalMap[g.goalType] = parseFloat(g.targetAmount)
  }
  const newBusinessCards = nb ? [
    { key: 'new_arr', label: t('forecasts.newBusiness.wonNewArr'), actual: parseFloat(nb.wonNewArr), target: nbGoalMap['new_arr'] || 0, isCurrency: true },
    { key: 'new_development', label: t('forecasts.newBusiness.wonDevelopment'), actual: parseFloat(nb.wonDevelopmentRevenue), target: nbGoalMap['new_development'] || 0, isCurrency: true },
    { key: 'new_deal_count', label: t('forecasts.newBusiness.wonDealCount'), actual: nb.wonDealCount, target: nbGoalMap['new_deal_count'] || 0, isCurrency: false },
  ] : []

  const formatForecastSubtitle = (oneOff: string | undefined, discounts: string | undefined) => {
    const fmt = (v: number) => new Intl.NumberFormat('de-DE', {
      style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 0,
    }).format(Math.abs(v))
    const oneOffVal = parseFloat(oneOff ?? '0')
    const discountsVal = parseFloat(discounts ?? '0')
    const parts: string[] = []
    if (oneOffVal > 0) parts.push(t('dashboard.kpis.inclOneOff', { amount: fmt(oneOffVal) }))
    if (discountsVal < 0) parts.push(t('dashboard.kpis.inclDiscounts', { amount: fmt(discountsVal) }))
    return parts.length > 0 ? parts.join('\n') : undefined
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('dashboard.title')}</h1>
        <HelpVideoButton />
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-8">
        <KPICard
          title={t('dashboard.kpis.totalActiveContracts')}
          value={kpis?.totalActiveContracts ?? 0}
          explanation={t('dashboard.kpis.totalActiveContractsExplanation')}
        />
        <KPICard
          title={t('dashboard.kpis.totalContractValue')}
          value={parseFloat(kpis?.totalContractValue ?? '0')}
          explanation={t('dashboard.kpis.totalContractValueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.annualRecurringRevenue')}
          value={parseFloat(kpis?.annualRecurringRevenue ?? '0')}
          explanation={t('dashboard.kpis.annualRecurringRevenueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.yearToDateRevenue')}
          value={parseFloat(kpis?.yearToDateRevenue ?? '0')}
          explanation={t('dashboard.kpis.yearToDateRevenueExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.currentYearForecast')}
          value={parseFloat(kpis?.currentYearForecast ?? '0')}
          subtitle={formatForecastSubtitle(kpis?.currentYearOneOff, kpis?.currentYearDiscounts)}
          explanation={t('dashboard.kpis.currentYearForecastExplanation')}
          isCurrency
        />
        <KPICard
          title={t('dashboard.kpis.nextYearForecast')}
          value={parseFloat(kpis?.nextYearForecast ?? '0')}
          subtitle={formatForecastSubtitle(kpis?.nextYearOneOff, kpis?.nextYearDiscounts)}
          explanation={t('dashboard.kpis.nextYearForecastExplanation')}
          isCurrency
        />
      </div>

      {/* New Business KPIs */}
      {nb && (nb.wonDealCount > 0 || parseFloat(nb.wonNewArr) > 0) && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3">{t('forecasts.newBusiness.title')}</h2>
          <div
            className="grid gap-4 md:grid-cols-3 cursor-pointer"
            onClick={() => navigate(`/contracts?newBusiness=true&wonYear=${currentYear}`)}
          >
            {newBusinessCards.map((card) => {
              const progress = card.target > 0 ? (card.actual / card.target) * 100 : null
              const diff = card.actual - card.target
              const overTarget = progress !== null && progress > 100

              return (
                <div key={card.key} className="rounded-lg border bg-card p-4 hover:border-blue-300 hover:shadow-sm transition-all">
                  <p className="text-sm font-medium text-muted-foreground">{card.label}</p>
                  <p className="mt-1 text-2xl font-semibold">
                    {card.isCurrency ? formatCurrency(card.actual.toString()) : card.actual}
                  </p>
                  {card.target > 0 && (
                    <>
                      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                        <span>{t('forecasts.goals.target')}: {card.isCurrency ? formatCurrency(card.target.toString()) : card.target}</span>
                        <span className={diff >= 0 ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
                          {diff >= 0 ? '+' : ''}{card.isCurrency ? formatCurrency(diff.toString()) : diff}
                        </span>
                      </div>
                      <div className="mt-2 relative h-2 w-full rounded-full bg-gray-200">
                        <div
                          className={`h-2 rounded-full transition-all ${
                            overTarget ? 'bg-emerald-500' : (progress ?? 0) >= 80 ? 'bg-blue-500' : 'bg-blue-400'
                          }`}
                          style={{ width: `${Math.min(progress ?? 0, 100)}%` }}
                        />
                      </div>
                      <p className={`mt-1 text-xs font-medium ${overTarget ? 'text-emerald-600' : 'text-muted-foreground'}`}>
                        {Math.round(progress!)}%
                      </p>
                    </>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

    </div>
  )
}
