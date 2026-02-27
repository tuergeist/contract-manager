import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Settings } from './Settings'
import { ForecastCacheSettings } from './ForecastCacheSettings'

export function GeneralSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/general/help-videos')) return 'helpVideos'
    if (location.pathname.includes('/general/performance')) return 'performance'
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
      </TabsList>

      <TabsContent value="contracts">
        <Settings showHeader={false} section="contracts" />
      </TabsContent>

      <TabsContent value="helpVideos">
        <Settings showHeader={false} section="helpVideos" />
      </TabsContent>

      <TabsContent value="performance">
        <ForecastCacheSettings />
      </TabsContent>
    </Tabs>
  )
}
