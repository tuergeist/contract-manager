import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Settings } from './Settings'

export function GeneralSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/general/time-tracking')) return 'timeTracking'
    if (location.pathname.includes('/general/email')) return 'email'
    if (location.pathname.includes('/general/contracts')) return 'contracts'
    if (location.pathname.includes('/general/help-videos')) return 'helpVideos'
    return 'hubspot'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'timeTracking':
        navigate('/settings/general/time-tracking')
        break
      case 'email':
        navigate('/settings/general/email')
        break
      case 'contracts':
        navigate('/settings/general/contracts')
        break
      case 'helpVideos':
        navigate('/settings/general/help-videos')
        break
      default:
        navigate('/settings/general')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="hubspot">{t('settings.generalTabs.hubspot')}</TabsTrigger>
        <TabsTrigger value="timeTracking">{t('settings.generalTabs.timeTracking')}</TabsTrigger>
        <TabsTrigger value="email">{t('settings.generalTabs.email')}</TabsTrigger>
        <TabsTrigger value="contracts">{t('settings.generalTabs.contracts')}</TabsTrigger>
        <TabsTrigger value="helpVideos">{t('settings.generalTabs.helpVideos')}</TabsTrigger>
      </TabsList>

      <TabsContent value="hubspot">
        <Settings showHeader={false} section="hubspot" />
      </TabsContent>

      <TabsContent value="timeTracking">
        <Settings showHeader={false} section="timeTracking" />
      </TabsContent>

      <TabsContent value="email">
        <Settings showHeader={false} section="email" />
      </TabsContent>

      <TabsContent value="contracts">
        <Settings showHeader={false} section="contracts" />
      </TabsContent>

      <TabsContent value="helpVideos">
        <Settings showHeader={false} section="helpVideos" />
      </TabsContent>
    </Tabs>
  )
}
