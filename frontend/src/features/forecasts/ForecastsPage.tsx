import { useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
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
    <Tabs value={activeTab} onValueChange={handleTabChange}>
      <TabsList>
        <TabsTrigger value="revenue">{t('forecasts.revenueTab')}</TabsTrigger>
        <TabsTrigger value="liquidity">{t('forecasts.liquidityTab')}</TabsTrigger>
      </TabsList>
      <TabsContent value="revenue">
        <RevenueForecast />
      </TabsContent>
      <TabsContent value="liquidity">
        <LiquidityForecast />
      </TabsContent>
    </Tabs>
  )
}
