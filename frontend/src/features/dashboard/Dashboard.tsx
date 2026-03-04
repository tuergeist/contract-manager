import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import { Loader2, AlertCircle, Info } from 'lucide-react'
import { KPICard } from './KPICard'
import { HelpVideoButton } from '@/components/HelpVideoButton'
import { formatCurrency } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

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
    priceIncreaseImpact(year: $year) {
      year
      totalArrImpact
      inflationArrImpact
      negotiatedArrImpact
      untaggedArrImpact
      itemCount
    }
    newBusinessGoals(year: $year) {
      id
      year
      goalType
      targetAmount
    }
    revenueGoals(year: $year) {
      id
      year
      revenueType
      targetAmount
    }
    revenueByStream(year: $year) {
      revenueType
      ytdActual
      fullYearForecast
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

interface PriceIncreaseImpact {
  year: number
  totalArrImpact: string
  inflationArrImpact: string
  negotiatedArrImpact: string
  untaggedArrImpact: string
  itemCount: number
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

interface RevenueGoal {
  id: number
  year: number
  revenueType: string
  targetAmount: string
}

interface RevenueStreamData {
  revenueType: string
  ytdActual: string
  fullYearForecast: string
}

interface DashboardKPIsData {
  dashboardKpis: DashboardKPIs
  priceIncreaseImpact: PriceIncreaseImpact
  newBusinessMetrics: NewBusinessMetrics
  newBusinessGoals: NewBusinessGoal[]
  revenueGoals: RevenueGoal[]
  revenueByStream: RevenueStreamData[]
}

export function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showInfoModal, setShowInfoModal] = useState(false)

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

  // Revenue goals maps
  const revenueGoalMap: Record<string, number> = {}
  for (const g of kpisData?.revenueGoals || []) {
    revenueGoalMap[g.revenueType] = parseFloat(g.targetAmount)
  }
  const streamDataMap: Record<string, { ytdActual: number; forecast: number }> = {}
  for (const s of kpisData?.revenueByStream || []) {
    streamDataMap[s.revenueType] = { ytdActual: parseFloat(s.ytdActual), forecast: parseFloat(s.fullYearForecast) }
  }
  const STANDARD_STREAMS = [
    { key: 'recurring', i18nKey: 'products.revenueTypes.recurring', explanationKey: 'dashboard.revenueGoals.recurringExplanation' },
    { key: 'advanced_development', i18nKey: 'products.revenueTypes.advancedDevelopment' },
    { key: 'training_implementation', i18nKey: 'products.revenueTypes.trainingImplementation' },
  ] as const
  const hasRevenueGoalsData = Object.keys(revenueGoalMap).length > 0 || Object.values(streamDataMap).some(s => s.forecast > 0)
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
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowInfoModal(true)}
            className="text-muted-foreground hover:text-foreground transition-colors p-1"
          >
            <Info className="h-5 w-5" />
          </button>
          <HelpVideoButton />
        </div>
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
      {nb && (nb.wonDealCount > 0 || parseFloat(nb.wonNewArr) > 0 || Object.keys(nbGoalMap).length > 0) && (
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

      {/* Price Increase Impact */}
      {(() => {
        const pi = kpisData?.priceIncreaseImpact
        const totalImpact = parseFloat(pi?.totalArrImpact ?? '0')
        if (!pi || totalImpact <= 0) return null
        return (
          <div className="mb-8">
            <h2 className="text-lg font-semibold mb-3">{t('dashboard.priceIncrease.title')}</h2>
            <div className="grid gap-4 md:grid-cols-3">
              <KPICard
                title={t('dashboard.priceIncrease.totalImpact')}
                value={totalImpact}
                explanation={t('dashboard.priceIncrease.totalImpactExplanation')}
                subtitle={t('dashboard.priceIncrease.itemCount', { count: pi.itemCount })}
                isCurrency
              />
              <KPICard
                title={t('dashboard.priceIncrease.inflation')}
                value={parseFloat(pi.inflationArrImpact)}
                explanation={t('dashboard.priceIncrease.inflationExplanation')}
                isCurrency
              />
              <KPICard
                title={t('dashboard.priceIncrease.negotiated')}
                value={parseFloat(pi.negotiatedArrImpact)}
                explanation={t('dashboard.priceIncrease.negotiatedExplanation')}
                isCurrency
              />
            </div>
          </div>
        )
      })()}

      {/* Revenue Goals */}
      {hasRevenueGoalsData && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-3">{t('dashboard.revenueGoals.title')}</h2>
          <div
            className="grid gap-4 md:grid-cols-3 cursor-pointer"
            onClick={() => navigate('/forecasts?tab=goals')}
          >
            {STANDARD_STREAMS.map((stream) => {
              const data = streamDataMap[stream.key]
              const target = revenueGoalMap[stream.key] || 0
              const forecast = data?.forecast ?? 0
              const progress = target > 0 ? (forecast / target) * 100 : null
              const diff = forecast - target
              const overTarget = progress !== null && progress > 100

              return (
                <div key={stream.key} className="rounded-lg border bg-card p-4 hover:border-blue-300 hover:shadow-sm transition-all">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-muted-foreground">{t(stream.i18nKey)}</p>
                    {'explanationKey' in stream && stream.explanationKey && (
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <button className="text-muted-foreground hover:text-foreground transition-colors">
                              <Info className="h-3.5 w-3.5" />
                            </button>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <p>{t(stream.explanationKey)}</p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    )}
                  </div>
                  <p className="mt-1 text-2xl font-semibold">
                    {formatCurrency(forecast.toString())}
                  </p>
                  {target > 0 ? (
                    <>
                      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                        <span>{t('forecasts.goals.target')}: {formatCurrency(target.toString())}</span>
                        <span className={diff >= 0 ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
                          {diff >= 0 ? '+' : ''}{formatCurrency(diff.toString())}
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
                  ) : (
                    <p className="mt-2 text-xs text-muted-foreground">
                      <span className="underline">{t('forecasts.goals.setGoals')}</span>
                    </p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Info Modal */}
      <Dialog open={showInfoModal} onOpenChange={setShowInfoModal}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{t('dashboard.info.title')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 text-sm">
            <div>
              <h3 className="font-semibold text-base mb-2">{t('dashboard.info.kpisSection')}</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.totalActiveContracts')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.totalActiveContractsExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.totalContractValue')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.totalContractValueExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.annualRecurringRevenue')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.annualRecurringRevenueExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.yearToDateRevenue')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.yearToDateRevenueExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.currentYearForecast')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.currentYearForecastExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('dashboard.kpis.nextYearForecast')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.nextYearForecastExplanation')}</dd>
                </div>
              </dl>
            </div>
            <div>
              <h3 className="font-semibold text-base mb-2">{t('forecasts.newBusiness.title')}</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="font-medium">{t('forecasts.newBusiness.wonNewArr')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.wonNewArrExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('forecasts.newBusiness.wonDevelopment')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.wonDevelopmentExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('forecasts.newBusiness.wonDealCount')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.kpis.wonDealCountExplanation')}</dd>
                </div>
              </dl>
            </div>
            <div>
              <h3 className="font-semibold text-base mb-2">{t('dashboard.revenueGoals.title')}</h3>
              <dl className="space-y-3">
                <div>
                  <dt className="font-medium">{t('products.revenueTypes.recurring')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.revenueGoals.recurringExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('products.revenueTypes.advancedDevelopment')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.revenueGoals.streamExplanation')}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t('products.revenueTypes.trainingImplementation')}</dt>
                  <dd className="text-muted-foreground">{t('dashboard.revenueGoals.streamExplanation')}</dd>
                </div>
              </dl>
            </div>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  )
}
