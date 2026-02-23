import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { RevenueForecast } from '@/features/forecast/RevenueForecast'
import { LiquidityForecast } from '@/features/liquidity'

export function ForecastsPage() {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const hasLiquidity = hasPermission('banking', 'read')
  const activeTab = searchParams.get('tab') || 'revenue'

  const handleTabChange = (value: string) => {
    setSearchParams(value === 'revenue' ? {} : { tab: value })
  }

  if (!hasLiquidity) {
    return <RevenueForecast />
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 border-b border-gray-200">
        <button
          onClick={() => handleTabChange('revenue')}
          className={`border-b-2 px-1 pb-2 text-sm font-medium ${
            activeTab === 'revenue'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
          }`}
        >
          {t('forecasts.revenueTab')}
        </button>
        <button
          onClick={() => handleTabChange('liquidity')}
          className={`border-b-2 px-1 pb-2 text-sm font-medium ${
            activeTab === 'liquidity'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
          }`}
        >
          {t('forecasts.liquidityTab')}
        </button>
      </div>
      {activeTab === 'revenue' && <RevenueForecast />}
      {activeTab === 'liquidity' && <LiquidityForecast />}
    </div>
  )
}
