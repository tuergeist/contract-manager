import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { RevenueForecast } from '@/features/forecast/RevenueForecast'
import { LiquidityForecast } from '@/features/liquidity'
import { RevenueGoalsDashboard } from './RevenueGoalsDashboard'

export function ForecastsPage() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const hasLiquidity = hasPermission('banking', 'read')
  const activeTab = searchParams.get('tab') || 'revenue'

  const handleTabChange = (value: string) => {
    setSearchParams(value === 'revenue' ? {} : { tab: value })
  }

  const tabClass = (tab: string) =>
    `border-b-2 px-1 pb-2 text-sm font-medium ${
      activeTab === tab
        ? 'border-blue-600 text-blue-600'
        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
    }`

  if (!hasLiquidity) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-4 border-b border-gray-200">
          <button onClick={() => handleTabChange('revenue')} className={tabClass('revenue')}>
            {t('forecasts.revenueTab')}
          </button>
          <button onClick={() => handleTabChange('goals')} className={tabClass('goals')}>
            {t('forecasts.goalsTab')}
          </button>
        </div>
        {activeTab === 'revenue' && <RevenueForecast />}
        {activeTab === 'goals' && <RevenueGoalsDashboard />}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 border-b border-gray-200">
        <button onClick={() => handleTabChange('revenue')} className={tabClass('revenue')}>
          {t('forecasts.revenueTab')}
        </button>
        <button onClick={() => handleTabChange('liquidity')} className={tabClass('liquidity')}>
          {t('forecasts.liquidityTab')}
        </button>
        <button onClick={() => handleTabChange('goals')} className={tabClass('goals')}>
          {t('forecasts.goalsTab')}
        </button>
      </div>
      {activeTab === 'revenue' && <RevenueForecast />}
      {activeTab === 'liquidity' && <LiquidityForecast />}
      {activeTab === 'goals' && <RevenueGoalsDashboard />}
    </div>
  )
}
