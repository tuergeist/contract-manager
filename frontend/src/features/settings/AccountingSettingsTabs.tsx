import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { RevenueGoalSettings } from './RevenueGoalSettings'
import { CostCenterSettings } from './CostCenterSettings'
import { SplitRuleSettings } from './SplitRuleSettings'
import { FteSnapshotSettings } from './FteSnapshotSettings'
import { DunningSettings } from './DunningSettings'

export function AccountingSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/accounting/cost-centers')) return 'costCenters'
    if (location.pathname.includes('/accounting/dunning')) return 'dunning'
    return 'revenueGoals'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'costCenters':
        navigate('/settings/accounting/cost-centers')
        break
      case 'dunning':
        navigate('/settings/accounting/dunning')
        break
      default:
        navigate('/settings/accounting')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="revenueGoals">{t('settings.accountingTabs.revenueGoals')}</TabsTrigger>
        <TabsTrigger value="costCenters">{t('settings.accountingTabs.costCenters')}</TabsTrigger>
        <TabsTrigger value="dunning">{t('settings.accountingTabs.dunning')}</TabsTrigger>
      </TabsList>

      <TabsContent value="revenueGoals">
        <RevenueGoalSettings />
      </TabsContent>

      <TabsContent value="costCenters">
        <div className="space-y-6">
          <CostCenterSettings />
          <SplitRuleSettings />
          <FteSnapshotSettings />
        </div>
      </TabsContent>

      <TabsContent value="dunning">
        <DunningSettings showHeader={false} />
      </TabsContent>
    </Tabs>
  )
}
