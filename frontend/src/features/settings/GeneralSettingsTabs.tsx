import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Settings } from './Settings'
import { TenantNameSettings } from './TenantNameSettings'
import { ForecastCacheSettings } from './ForecastCacheSettings'
import { RevenueGoalSettings } from './RevenueGoalSettings'
import { TenantSecuritySettings } from './TenantSecuritySettings'

export function GeneralSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/general/help-videos')) return 'helpVideos'
    if (location.pathname.includes('/general/performance')) return 'performance'
    if (location.pathname.includes('/general/revenue-goals')) return 'revenueGoals'
    if (location.pathname.includes('/general/security')) return 'security'
    return 'contracts'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'helpVideos':
        navigate('/settings/general/help-videos')
        break
      case 'performance':
        navigate('/settings/general/performance')
        break
      case 'revenueGoals':
        navigate('/settings/general/revenue-goals')
        break
      case 'security':
        navigate('/settings/general/security')
        break
      default:
        navigate('/settings/general')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="contracts">{t('settings.generalTabs.contracts')}</TabsTrigger>
        <TabsTrigger value="helpVideos">{t('settings.generalTabs.helpVideos')}</TabsTrigger>
        <TabsTrigger value="performance">{t('settings.generalTabs.performance')}</TabsTrigger>
        <TabsTrigger value="revenueGoals">{t('settings.generalTabs.revenueGoals')}</TabsTrigger>
        <TabsTrigger value="security">{t('settings.generalTabs.security')}</TabsTrigger>
      </TabsList>

      <TabsContent value="contracts">
        <div className="space-y-6">
          <TenantNameSettings />
          <Settings showHeader={false} section="contracts" />
        </div>
      </TabsContent>

      <TabsContent value="helpVideos">
        <Settings showHeader={false} section="helpVideos" />
      </TabsContent>

      <TabsContent value="performance">
        <ForecastCacheSettings />
      </TabsContent>

      <TabsContent value="revenueGoals">
        <RevenueGoalSettings />
      </TabsContent>

      <TabsContent value="security">
        <TenantSecuritySettings />
      </TabsContent>
    </Tabs>
  )
}
